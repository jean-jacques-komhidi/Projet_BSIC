# -*- coding: utf-8 -*-
"""
Service de l'assistant conversationnel (CrediBot) de CREDISCORE.

L'assistant repond aux questions de l'agent en langage naturel. On lui fournit
un contexte riche (statistiques globales + liste des clients et de leurs
analyses recentes) pour qu'il puisse repondre precisement, y compris sur des
clients ou dossiers particuliers.

Le modele de langage est appele via l'API gratuite de Groq.
"""

import os
import json
from groq import Groq
from sqlalchemy.orm import Session
from sqlalchemy import func
from dotenv import load_dotenv

from . import models

load_dotenv()

_cle = os.getenv("GROQ_API_KEY")
client_groq = Groq(api_key=_cle) if _cle else None
MODELE_LLM = "openai/gpt-oss-120b"


# ---------------------------------------------------------------------------
# Construction du contexte fourni a l'assistant
# ---------------------------------------------------------------------------
def _statistiques(db: Session) -> str:
    """Statistiques globales de l'application."""
    total_analyses = db.query(models.Analyse).count()
    total_clients = db.query(models.Client).count()
    accordes = db.query(models.Analyse).filter(models.Analyse.decision == "ACCORDE").count()
    refuses = db.query(models.Analyse).filter(models.Analyse.decision == "REFUSE").count()
    rf = db.query(models.Analyse).filter(models.Analyse.classe_risque == "faible").count()
    rm = db.query(models.Analyse).filter(models.Analyse.classe_risque == "moyen").count()
    re = db.query(models.Analyse).filter(models.Analyse.classe_risque == "eleve").count()
    proba = db.query(func.avg(models.Analyse.probabilite_defaut)).scalar()
    proba = round(proba * 100, 1) if proba else 0

    return (
        f"STATISTIQUES GLOBALES :\n"
        f"- Clients enregistres : {total_clients}\n"
        f"- Analyses realisees : {total_analyses}\n"
        f"- Credits accordes : {accordes} | refuses : {refuses}\n"
        f"- Repartition du risque : {rf} faible, {rm} moyen, {re} eleve\n"
        f"- Probabilite moyenne de defaut : {proba} %"
    )


def _liste_clients(db: Session, limite=40) -> str:
    """Liste des clients avec leur derniere analyse (pour les questions ciblees)."""
    clients = db.query(models.Client).limit(limite).all()
    if not clients:
        return "Aucun client enregistre."

    lignes = ["LISTE DES CLIENTS ET DE LEUR DERNIERE ANALYSE :"]
    for c in clients:
        derniere = db.query(models.Analyse).filter(
            models.Analyse.client_id == c.id
        ).order_by(models.Analyse.date_analyse.desc()).first()
        if derniere:
            proba = round(derniere.probabilite_defaut * 100, 1)
            infos = (f"decision {derniere.decision}, risque {derniere.classe_risque}, "
                     f"probabilite de defaut {proba}%")
        else:
            infos = "aucune analyse"
        prof = c.profession or "profession inconnue"
        age = f"{int(c.age)} ans" if c.age else "age inconnu"
        lignes.append(f"- {c.nom} ({prof}, {age}) : {infos}")
    return "\n".join(lignes)


def _contexte_dossier(db: Session, analyse_id: int) -> str:
    """Contexte detaille d'une analyse precise (pour une question sur un dossier)."""
    analyse = db.query(models.Analyse).filter(models.Analyse.id == analyse_id).first()
    if not analyse:
        return None
    client = db.query(models.Client).filter(models.Client.id == analyse.client_id).first()
    facteurs = ""
    if analyse.facteurs_explicatifs:
        fs = json.loads(analyse.facteurs_explicatifs)
        facteurs = ", ".join(
            f"{f['variable']} ({'augmente' if f['contribution']>0 else 'reduit'} le risque)"
            for f in fs[:5])
    return (
        f"DOSSIER ANALYSE N {analyse.id} :\n"
        f"- Client : {client.nom if client else 'inconnu'}\n"
        f"- Decision : {analyse.decision}\n"
        f"- Probabilite de defaut : {round(analyse.probabilite_defaut*100,1)} %\n"
        f"- Classe de risque : {analyse.classe_risque}\n"
        f"- Explication : {analyse.explication or 'non disponible'}\n"
        f"- Facteurs determinants : {facteurs}"
    )


# ---------------------------------------------------------------------------
# Le prompt systeme (professionnel)
# ---------------------------------------------------------------------------
PROMPT_SYSTEME = """Tu es CrediBot, l'assistant intelligent de CREDISCORE, l'application de scoring credit de la BSIC Tchad (Banque Sahelo-Saharienne pour l'Investissement et le Commerce).

TON ROLE :
Tu aides les agents de credit et les administrateurs a comprendre les donnees, les analyses de credit et les decisions. Tu es leur collegue de confiance.

TON COMPORTEMENT :
- Tu es professionnel, precis et fiable, mais aussi chaleureux et accessible.
- Tu ne dis "bonjour" ou ne te presentes QU'UNE SEULE FOIS, au tout premier message d'une conversation. Ensuite, tu vas droit au but, comme dans une vraie discussion.
- Tu reponds de maniere concise et claire. Pas de bavardage inutile.
- Tu bases TOUJOURS tes reponses sur les donnees fournies dans le contexte. Tu ne inventes jamais de chiffres.
- Si une information n'est pas dans le contexte, tu le dis honnetement : "Je n'ai pas cette information dans les donnees actuelles."
- Tu peux mettre en forme tes reponses en Markdown (listes avec des tirets, gras avec **, tableaux Markdown) pour plus de clarte.
- IMPORTANT : utilise UNIQUEMENT du Markdown, JAMAIS de balises HTML comme <br>, <table> ou <div>. Pour un retour a la ligne dans une cellule, mets le texte sur la meme ligne ou utilise plusieurs lignes.
- Garde tes reponses bien structurees mais pas trop longues.
- Quand on te parle d'un client par son nom, tu cherches ses informations dans la liste des clients fournie.

TON EXPERTISE :
Tu comprends le scoring credit : la probabilite de defaut, les classes de risque (faible, moyen, eleve), les decisions (accorde/refuse), et le fait qu'un credit est refuse quand le risque depasse le seuil.

Reponds toujours en francais, de maniere naturelle et utile."""


def repondre(db: Session, question: str, analyse_id: int = None, historique: list = None) -> str:
    """Repond a une question de l'agent, avec un contexte riche et le contexte
    de la conversation en cours."""
    if client_groq is None:
        return ("L'assistant n'est pas configure : la cle GROQ_API_KEY est absente du fichier .env.")

    # Construire le contexte
    if analyse_id is not None:
        contexte = _contexte_dossier(db, analyse_id)
        if contexte is None:
            return f"Je ne trouve pas l'analyse N {analyse_id}."
    else:
        # Contexte global : statistiques + liste des clients et leurs analyses
        contexte = _statistiques(db) + "\n\n" + _liste_clients(db)

    try:
        liste_messages = [
            {"role": "system", "content": PROMPT_SYSTEME + "\n\nCONTEXTE ACTUEL DES DONNEES :\n" + contexte},
        ]
        if historique:
            for msg in historique:
                role = "assistant" if msg.get("role") == "assistant" else "user"
                liste_messages.append({"role": role, "content": msg.get("contenu", "")})
        liste_messages.append({"role": "user", "content": question})

        reponse = client_groq.chat.completions.create(
            model=MODELE_LLM,
            messages=liste_messages,
            temperature=0.4,
            max_tokens=600,
        )
        return reponse.choices[0].message.content.strip()
    except Exception as e:
        from .logging_config import logger
        message = str(e).lower()
        logger.error(f"Erreur chatbot (Groq) : {e}")
        if "rate limit" in message or "quota" in message or "429" in message:
            return ("L'assistant est temporairement surcharge (trop de demandes). "
                    "Reessayez dans quelques instants.")
        if "authentication" in message or "api key" in message or "401" in message:
            return ("L'assistant n'est pas correctement configure (cle API invalide). "
                    "Contactez l'administrateur.")
        return "L'assistant est momentanement indisponible. Reessayez plus tard."
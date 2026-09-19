# -*- coding: utf-8 -*-
"""
Service de l'assistant conversationnel (chatbot) de CREDISCORE.

L'assistant repond aux questions de l'agent en langage naturel, selon deux
mecanismes :
  a) les questions sur les donnees (statistiques) : on calcule un resume de
     la base et on le fournit au modele de langage, qui formule la reponse ;
  b) les questions sur un dossier precis : on fournit au modele le contexte de
     l'analyse concernee (score, decision, explication), et il repond a partir
     de ces donnees reelles (approche RAG).

Le modele de langage est appele via l'API gratuite de Groq. Cette approche
evite de laisser le modele generer directement du SQL, ce qui est plus sur.
"""

import os
import json
from groq import Groq
from sqlalchemy.orm import Session
from sqlalchemy import func
from dotenv import load_dotenv

from . import models

load_dotenv()

# Client Groq (la cle est lue depuis le .env)
_cle = os.getenv("GROQ_API_KEY")
client_groq = Groq(api_key=_cle) if _cle else None

# Modele de langage utilise (un modele gratuit et performant de Groq)
MODELE_LLM = "openai/gpt-oss-120b"


def _resume_base(db: Session) -> str:
    """Calcule un resume statistique de la base pour repondre aux questions
    sur les donnees. Ce resume est fourni au modele comme contexte."""
    total_analyses = db.query(models.Analyse).count()
    total_clients = db.query(models.Client).count()
    accordes = db.query(models.Analyse).filter(
        models.Analyse.decision == "ACCORDE").count()
    refuses = db.query(models.Analyse).filter(
        models.Analyse.decision == "REFUSE").count()
    # Repartition par classe de risque
    risque_faible = db.query(models.Analyse).filter(
        models.Analyse.classe_risque == "faible").count()
    risque_moyen = db.query(models.Analyse).filter(
        models.Analyse.classe_risque == "moyen").count()
    risque_eleve = db.query(models.Analyse).filter(
        models.Analyse.classe_risque == "eleve").count()
    # Probabilite moyenne de defaut
    proba_moy = db.query(func.avg(models.Analyse.probabilite_defaut)).scalar()
    proba_moy = round(proba_moy * 100, 1) if proba_moy else 0

    resume = f"""Donnees actuelles de l'application CREDISCORE :
- Nombre total de clients : {total_clients}
- Nombre total d'analyses realisees : {total_analyses}
- Credits accordes : {accordes}
- Credits refuses : {refuses}
- Repartition du risque : {risque_faible} faible, {risque_moyen} moyen, {risque_eleve} eleve
- Probabilite moyenne de defaut : {proba_moy} %"""
    return resume


def _contexte_dossier(db: Session, analyse_id: int) -> str:
    """Prepare le contexte d'une analyse precise pour une question sur un dossier."""
    analyse = db.query(models.Analyse).filter(
        models.Analyse.id == analyse_id).first()
    if not analyse:
        return None
    client = db.query(models.Client).filter(
        models.Client.id == analyse.client_id).first()

    facteurs = ""
    if analyse.facteurs_explicatifs:
        fs = json.loads(analyse.facteurs_explicatifs)
        facteurs = ", ".join(
            f"{f['variable']} ({'reduit' if f['contribution']<0 else 'augmente'} le risque)"
            for f in fs[:5])

    contexte = f"""Analyse N {analyse.id} :
- Client : {client.nom if client else 'inconnu'}
- Decision : {analyse.decision}
- Probabilite de defaut : {round(analyse.probabilite_defaut*100,1)} %
- Classe de risque : {analyse.classe_risque}
- Explication : {analyse.explication or 'non disponible'}
- Facteurs determinants : {facteurs}"""
    return contexte


def repondre(db: Session, question: str, analyse_id: int = None) -> str:
    """Repond a une question de l'agent.

    - Si analyse_id est fourni, la question porte sur ce dossier precis (RAG).
    - Sinon, la question porte sur les donnees generales (statistiques).
    """
    if client_groq is None:
        return ("L'assistant n'est pas configure : la cle GROQ_API_KEY est "
                "absente du fichier .env.")

    # Preparer le contexte selon le type de question
    if analyse_id is not None:
        contexte = _contexte_dossier(db, analyse_id)
        if contexte is None:
            return f"L'analyse N {analyse_id} est introuvable."
        systeme = (
            "Tu es l'assistant d'une application bancaire de scoring de credit. "
            "Reponds a la question de l'agent en te basant uniquement sur le "
            "contexte du dossier fourni. Sois clair, concis et professionnel. "
            "Reponds en francais.")
    else:
        contexte = _resume_base(db)
        systeme = (
            "Tu es l'assistant d'une application bancaire de scoring de credit. "
            "Reponds a la question de l'agent en te basant sur les donnees "
            "statistiques fournies. Sois clair, concis et professionnel. "
            "Si la donnee demandee n'est pas dans le resume, dis-le honnetement. "
            "Reponds en francais.")

    # Appel au modele de langage
    try:
        reponse = client_groq.chat.completions.create(
            model=MODELE_LLM,
            messages=[
                {"role": "system", "content": systeme},
                {"role": "user", "content": f"Contexte :\n{contexte}\n\nQuestion : {question}"},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        return reponse.choices[0].message.content.strip()
    except Exception as e:
        return f"Une erreur est survenue lors de l'appel a l'assistant : {e}"
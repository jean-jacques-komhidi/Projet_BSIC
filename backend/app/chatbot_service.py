# -*- coding: utf-8 -*-
"""
Service de l'assistant conversationnel (CrediBot) de CREDISCORE.

L'assistant repond aux questions de l'agent en langage naturel. On lui fournit
un contexte riche (statistiques globales + liste des clients et de leurs
analyses recentes, taux de reussite des predictions) pour qu'il puisse repondre
precisement, y compris sur des clients ou dossiers particuliers.

Le modele de langage est appele via l'API gratuite de Groq.
"""

import os
import json
import unicodedata
from groq import Groq
from sqlalchemy.orm import Session
from sqlalchemy import func

from . import models

_cle = os.getenv("GROQ_API_KEY")
client_groq = Groq(api_key=_cle) if _cle else None
MODELE_LLM = "openai/gpt-oss-120b"

# Seuil de decision reel du modele : un credit est refuse au-dela de cette
# probabilite de defaut. Doit rester aligne avec le backend et le frontend.
SEUIL_DECISION = 0.30

# Nombre maximal de messages d'historique reinjectes dans le prompt (pour
# garder une latence et une consommation de tokens raisonnables).
MAX_HISTORIQUE = 10


# ---------------------------------------------------------------------------
# Outils de normalisation (robustesse aux variantes de libelles)
# ---------------------------------------------------------------------------
def _normaliser(valeur) -> str:
    """Minuscule sans accent : 'ACCORDÉ' -> 'accorde', 'Élevé' -> 'eleve'.
    Rend les comparaisons insensibles a la casse et aux accents, ce qui evite
    les compteurs faux selon la facon dont les libelles sont stockes en base."""
    if valeur is None:
        return ""
    texte = str(valeur)
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return texte.strip().lower()


def _nettoyer_html(texte: str) -> str:
    """Filet de securite : si le modele glisse malgre tout une balise <br> dans
    une reponse, on la convertit en retour a la ligne reel, et on retire les
    autres balises HTML les plus courantes qui s'afficheraient en texte brut."""
    if not texte:
        return texte
    import re
    # <br>, <br/>, <br /> -> retour a la ligne
    texte = re.sub(r"<\s*br\s*/?\s*>", "\n", texte, flags=re.IGNORECASE)
    # retirer quelques balises de structure qui n'ont pas de sens en Markdown
    texte = re.sub(r"</?\s*(div|span|table|tr|td|th|ul|ol|li)[^>]*>", "", texte, flags=re.IGNORECASE)
    return texte.strip()


def _charger_json(donnee):
    """Charge un champ JSON qui peut etre deja un objet Python, une chaine
    JSON, ou vide/invalide. Ne leve jamais d'exception."""
    if not donnee:
        return None
    if isinstance(donnee, (list, dict)):
        return donnee
    try:
        return json.loads(donnee)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Construction du contexte fourni a l'assistant
# ---------------------------------------------------------------------------
def _statistiques(db: Session) -> str:
    """Statistiques globales de l'application (comptage robuste cote Python
    pour ne pas dependre du format exact des libelles stockes)."""
    analyses = db.query(
        models.Analyse.decision,
        models.Analyse.classe_risque,
        models.Analyse.probabilite_defaut,
        models.Analyse.resultat_reel,
    ).all()

    total_analyses = len(analyses)
    total_clients = db.query(models.Client).count()

    accordes = refuses = 0
    rf = rm = re_ = rte = 0
    somme_proba = 0.0
    n_proba = 0
    # Suivi de la boucle MLOps (point 8)
    resolus = corrects = 0

    for dec, risque, proba, reel in analyses:
        d = _normaliser(dec)
        if d.startswith("accord"):
            accordes += 1
        elif d.startswith("refus"):
            refuses += 1

        r = _normaliser(risque)
        if "faible" in r:
            rf += 1
        elif "moyen" in r or "modere" in r:
            rm += 1
        elif "tres eleve" in r:
            rte += 1
        elif "eleve" in r:
            re_ += 1

        if proba is not None:
            somme_proba += proba
            n_proba += 1

        # Prediction consideree juste si : refus d'un dossier qui a fait defaut,
        # ou accord d'un dossier qui a ete rembourse.
        rr = _normaliser(reel)
        if rr in ("defaut", "rembourse", "rembourse"):
            resolus += 1
            a_fait_defaut = rr.startswith("defaut")
            a_ete_refuse = d.startswith("refus")
            if a_fait_defaut == a_ete_refuse:
                corrects += 1

    proba_moy = round((somme_proba / n_proba) * 100, 1) if n_proba else 0

    lignes = [
        "STATISTIQUES GLOBALES :",
        f"- Clients enregistres : {total_clients}",
        f"- Analyses realisees : {total_analyses}",
        f"- Credits accordes : {accordes} | refuses : {refuses}",
        f"- Repartition du risque : {rf} faible, {rm} moyen/modere, "
        f"{re_} eleve, {rte} tres eleve",
        f"- Probabilite moyenne de defaut : {proba_moy} %",
    ]
    if resolus:
        taux = round(corrects / resolus * 100, 1)
        lignes.append(
            f"- Suivi des predictions : {resolus} dossiers a l'issue connue, "
            f"dont {corrects} bien predits ({taux} % de predictions justes)"
        )
    return "\n".join(lignes)


def _liste_clients(db: Session, limite=40) -> str:
    """Liste des clients avec leur derniere analyse (pour les questions ciblees).

    Chargement en 2 requetes au lieu de N+1 : toutes les analyses des clients
    sont recuperees en une fois, puis la plus recente est retenue par client."""
    clients = db.query(models.Client).limit(limite).all()
    if not clients:
        return "Aucun client enregistre."

    ids = [c.id for c in clients]
    # Toutes les analyses de ces clients, triees par date decroissante.
    analyses = (
        db.query(models.Analyse)
        .filter(models.Analyse.client_id.in_(ids))
        .order_by(models.Analyse.date_analyse.desc())
        .all()
    )
    # On garde la premiere rencontree par client = la plus recente.
    derniere_par_client = {}
    for a in analyses:
        if a.client_id not in derniere_par_client:
            derniere_par_client[a.client_id] = a

    lignes = ["LISTE DES CLIENTS ET DE LEUR DERNIERE ANALYSE :"]
    for c in clients:
        derniere = derniere_par_client.get(c.id)
        if derniere:
            proba = round(derniere.probabilite_defaut * 100, 1)
            infos = (f"decision {derniere.decision}, risque {derniere.classe_risque}, "
                     f"probabilite de defaut {proba}%")
            reel = _normaliser(derniere.resultat_reel)
            if reel.startswith("defaut"):
                infos += ", issue reelle : DEFAUT"
            elif reel.startswith("rembours"):
                infos += ", issue reelle : rembourse"
        else:
            infos = "aucune analyse"
        prof = c.profession or "profession inconnue"
        age = f"{int(c.age)} ans" if c.age else "age inconnu"
        lignes.append(f"- {c.nom} ({prof}, {age}) : {infos}")
    return "\n".join(lignes)


def _contexte_dossier(db: Session, analyse_id: int) -> str:
    """Contexte detaille d'une analyse precise (pour une question sur un dossier).
    Complete par un rappel des statistiques globales pour permettre les
    comparaisons (ex : 'par rapport a la moyenne')."""
    analyse = db.query(models.Analyse).filter(models.Analyse.id == analyse_id).first()
    if not analyse:
        return None
    client = db.query(models.Client).filter(models.Client.id == analyse.client_id).first()

    facteurs = ""
    fs = _charger_json(analyse.facteurs_explicatifs)
    if fs:
        try:
            facteurs = ", ".join(
                f"{f['variable']} ({'augmente' if f.get('contribution', 0) > 0 else 'reduit'} le risque)"
                for f in fs[:5]
            )
        except (TypeError, KeyError):
            facteurs = ""

    reel = _normaliser(analyse.resultat_reel)
    if reel.startswith("defaut"):
        issue = "DEFAUT (le client n'a pas rembourse)"
    elif reel.startswith("rembours"):
        issue = "rembourse (le client a bien rembourse)"
    else:
        issue = "pas encore connue"

    bloc_dossier = (
        f"DOSSIER ANALYSE N {analyse.id} :\n"
        f"- Client : {client.nom if client else 'inconnu'}\n"
        f"- Decision : {analyse.decision}\n"
        f"- Probabilite de defaut : {round(analyse.probabilite_defaut * 100, 1)} %\n"
        f"- Classe de risque : {analyse.classe_risque}\n"
        f"- Issue reelle : {issue}\n"
        f"- Explication : {analyse.explication or 'non disponible'}\n"
        f"- Facteurs determinants : {facteurs or 'non disponibles'}"
    )
    # On ajoute les stats globales pour les questions de comparaison.
    return bloc_dossier + "\n\n" + _statistiques(db)


# ---------------------------------------------------------------------------
# Le prompt systeme (professionnel)
# ---------------------------------------------------------------------------
PROMPT_SYSTEME = f"""Tu es CrediBot, l'assistant intelligent de CREDISCORE, l'application de scoring credit de la BSIC Tchad (Banque Sahelo-Saharienne pour l'Investissement et le Commerce).

TON ROLE :
Tu aides les agents de credit et les administrateurs a comprendre les donnees, les analyses de credit et les decisions. Tu es leur collegue de confiance.

TON COMPORTEMENT :
- Tu es professionnel, precis et fiable, mais aussi chaleureux et accessible.
- Tu ne dis "bonjour" ou ne te presentes QU'UNE SEULE FOIS, au tout premier message d'une conversation. Ensuite, tu vas droit au but, comme dans une vraie discussion.
- Tu reponds de maniere concise et claire. Pas de bavardage inutile.
- Tu bases TOUJOURS tes reponses sur les donnees fournies dans le contexte. Tu n'inventes jamais de chiffres.
- Si une information n'est pas dans le contexte, tu le dis honnetement : "Je n'ai pas cette information dans les donnees actuelles."
- Tu peux mettre en forme tes reponses en Markdown (listes avec des tirets, gras avec **, titres avec ##, tableaux Markdown) pour plus de clarte.
- REGLE ABSOLUE SUR LE HTML : n'utilise JAMAIS de balises HTML, en particulier JAMAIS de <br>, <table>, <div> ou <ul>. L'interface n'affiche pas le HTML : une balise <br> apparaitrait telle quelle a l'ecran et donnerait une reponse laide.
- REGLE SUR LES TABLEAUX : n'utilise un tableau Markdown QUE lorsque chaque cellule tient en une seule ligne courte (un mot, un chiffre, une courte expression). Des qu'une cellule contiendrait plusieurs idees, plusieurs phrases ou une liste, n'utilise PAS de tableau : structure plutot ta reponse en sections, avec un titre en gras ou en ## par element, puis des puces "- " en dessous. Ne mets jamais de <br> ni de puces a l'interieur d'une cellule de tableau.
- Garde tes reponses bien structurees mais pas trop longues.
- Quand on te parle d'un client par son nom, tu cherches ses informations dans la liste des clients fournie.

TON EXPERTISE :
Tu comprends le scoring credit : la probabilite de defaut, les classes de risque (faible, moyen, eleve, tres eleve), les decisions (accorde/refuse), et le fait qu'un credit est refuse quand la probabilite de defaut depasse le seuil de decision, fixe a {int(SEUIL_DECISION * 100)} %. Un dossier dont la probabilite de defaut depasse {int(SEUIL_DECISION * 100)} % est donc refuse ; en dessous, il est accorde.
Tu comprends aussi la notion d'issue reelle : une fois un credit suivi, on sait s'il a ete rembourse ou s'il a fait defaut, ce qui permet de mesurer si les predictions etaient justes.

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
        # On ne garde que les derniers echanges pour limiter la latence et les tokens.
        if historique:
            for msg in historique[-MAX_HISTORIQUE:]:
                role = "assistant" if msg.get("role") == "assistant" else "user"
                contenu = msg.get("contenu", "")
                if contenu:
                    liste_messages.append({"role": role, "content": contenu})
        liste_messages.append({"role": "user", "content": question})

        reponse = client_groq.chat.completions.create(
            model=MODELE_LLM,
            messages=liste_messages,
            temperature=0.4,
            max_tokens=1000,
        )
        return _nettoyer_html(reponse.choices[0].message.content.strip())
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
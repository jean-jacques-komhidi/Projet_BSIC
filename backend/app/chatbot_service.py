# -*- coding: utf-8 -*-
"""
Service de l'assistant conversationnel (CrediBot) de CREDISCORE.

L'assistant repond aux questions de l'agent en langage naturel. On lui fournit
un contexte riche (statistiques globales, fiches des clients cites dans la
question, apercu des clients recents, utilisateur connecte) pour qu'il puisse
repondre precisement.

Le modele de langage est appele via l'API de Groq, un service externe. Pour
respecter le secret bancaire, les noms des clients ne lui sont JAMAIS envoyes :
ils sont remplaces par un identifiant ("Client#12") avant l'envoi, puis remis
en clair dans la reponse affichee a l'agent (pseudonymisation).
"""

import os
import re
import json
import unicodedata
from groq import Groq
from sqlalchemy.orm import Session

from . import models
# Seuils lus directement dans le service du modele : le chatbot explique ainsi
# toujours les decisions avec les memes seuils que ceux reellement appliques.
from .model_service import SEUIL_DECISION, SEUIL_RISQUE_FAIBLE

_cle = os.getenv("GROQ_API_KEY")
client_groq = Groq(api_key=_cle) if _cle else None
MODELE_LLM = "openai/gpt-oss-120b"

# Nombre maximal de messages d'historique reinjectes dans le prompt (pour
# garder une latence et une consommation de tokens raisonnables).
MAX_HISTORIQUE = 10

# Apercu des clients recents envoye a chaque question (les clients cites par
# leur nom sont TOUJOURS ajoutes en plus, quel que soit leur nombre total).
NB_CLIENTS_APERCU = 40
# Nombre maximal de fiches detaillees (clients cites) par question.
NB_FICHES_MAX = 5
# Nombre d'analyses detaillees par fiche client.
NB_ANALYSES_PAR_FICHE = 5


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


def _pct(proba) -> str:
    return f"{round((proba or 0) * 100, 1)} %"


# ---------------------------------------------------------------------------
# Pseudonymisation des clients (secret bancaire)
# ---------------------------------------------------------------------------
class Pseudonymes:
    """Remplace les noms des clients par 'Client#<id>' avant l'envoi au modele
    de langage, et retablit les vrais noms dans sa reponse."""

    MOTIF_JETON = re.compile(r"Client\s*#\s*(\d+)", re.IGNORECASE)
    LONGUEUR_MIN_MOT = 4  # un mot de nom plus court est trop ambigu

    def __init__(self, clients):
        """clients : liste de couples (id, nom)."""
        self.noms = {cid: nom.strip() for cid, nom in clients if nom and nom.strip()}

        # Mots de nom qui identifient UN SEUL client (ex : un nom de famille
        # rare) : permettent de reconnaitre "Mahamat" pour "Ali Mahamat".
        occurrences = {}
        for cid, nom in self.noms.items():
            for mot in set(_normaliser(nom).split()):
                if len(mot) >= self.LONGUEUR_MIN_MOT:
                    occurrences.setdefault(mot, set()).add(cid)
        self.mots_uniques = {mot: ids.pop() for mot, ids in occurrences.items() if len(ids) == 1}

    @staticmethod
    def jeton(cid) -> str:
        return f"Client#{cid}"

    def clients_cites(self, texte: str) -> list:
        """Identifiants des clients cites dans le texte (nom complet ou mot de
        nom propre a un seul client), dans l'ordre d'apparition."""
        norm = " " + re.sub(r"[^a-z0-9]+", " ", _normaliser(texte)) + " "
        trouves = {}
        for cid, nom in self.noms.items():
            nom_norm = " " + re.sub(r"[^a-z0-9]+", " ", _normaliser(nom)).strip() + " "
            pos = norm.find(nom_norm)
            if pos >= 0:
                trouves[cid] = pos
        for mot, cid in self.mots_uniques.items():
            pos = norm.find(f" {mot} ")
            if pos >= 0 and cid not in trouves:
                trouves[cid] = pos
        # Les jetons deja presents (ex : historique) comptent aussi
        for m in self.MOTIF_JETON.finditer(texte):
            cid = int(m.group(1))
            if cid in self.noms and cid not in trouves:
                trouves[cid] = len(norm)
        return [cid for cid, _ in sorted(trouves.items(), key=lambda x: x[1])]

    def masquer(self, texte: str) -> str:
        """Remplace les noms (complets, puis mots propres a un client) par leur jeton."""
        if not texte:
            return texte
        for cid, nom in sorted(self.noms.items(), key=lambda x: -len(x[1])):
            texte = re.sub(re.escape(nom), self.jeton(cid), texte, flags=re.IGNORECASE)
        # Mots isoles : on compare sans accents, mot par mot
        def remplacer_mot(m):
            cid = self.mots_uniques.get(_normaliser(m.group(0)))
            return self.jeton(cid) if cid is not None else m.group(0)
        return re.sub(r"[^\W\d_]{%d,}" % self.LONGUEUR_MIN_MOT, remplacer_mot, texte)

    def demasquer(self, texte: str) -> str:
        """Remet les vrais noms a la place des jetons dans la reponse."""
        if not texte:
            return texte
        return self.MOTIF_JETON.sub(
            lambda m: self.noms.get(int(m.group(1)), m.group(0)), texte)


# ---------------------------------------------------------------------------
# Construction du contexte fourni a l'assistant
# ---------------------------------------------------------------------------
def _issue(resultat_reel) -> str:
    r = _normaliser(resultat_reel)
    if r.startswith("defaut"):
        return "DEFAUT (n'a pas rembourse)"
    if r.startswith("rembours"):
        return "rembourse"
    return "pas encore connue"


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
    rf = rm = re_ = 0
    somme_proba = 0.0
    n_proba = 0
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
        elif "eleve" in r:
            re_ += 1

        if proba is not None:
            somme_proba += proba
            n_proba += 1

        # Prediction consideree juste si : refus d'un dossier qui a fait defaut,
        # ou accord d'un dossier qui a ete rembourse.
        rr = _normaliser(reel)
        if rr.startswith("defaut") or rr.startswith("rembours"):
            resolus += 1
            if rr.startswith("defaut") == d.startswith("refus"):
                corrects += 1

    proba_moy = round((somme_proba / n_proba) * 100, 1) if n_proba else 0

    lignes = [
        "STATISTIQUES GLOBALES :",
        f"- Clients enregistres : {total_clients}",
        f"- Analyses realisees : {total_analyses}",
        f"- Credits accordes : {accordes} | refuses : {refuses}",
        f"- Repartition du risque : {rf} faible, {rm} moyen, {re_} eleve",
        f"- Probabilite moyenne de defaut : {proba_moy} %",
    ]
    if resolus:
        taux = round(corrects / resolus * 100, 1)
        lignes.append(
            f"- Suivi des predictions : {resolus} dossiers a l'issue connue, "
            f"dont {corrects} bien predits ({taux} % de predictions justes)"
        )
    return "\n".join(lignes)


def _description_client(c) -> str:
    prof = c.profession or "profession inconnue"
    age = f"{int(c.age)} ans" if c.age else "age inconnu"
    return f"{prof}, {age}"


def _fiches_clients(db: Session, ids: list) -> str:
    """Fiches detaillees des clients cites dans la question."""
    if not ids:
        return ""
    clients = {c.id: c for c in db.query(models.Client).filter(models.Client.id.in_(ids)).all()}
    blocs = ["FICHES DES CLIENTS CITES DANS LA QUESTION :"]
    for cid in ids:
        c = clients.get(cid)
        if not c:
            continue
        analyses = (
            db.query(models.Analyse)
            .filter(models.Analyse.client_id == cid)
            .order_by(models.Analyse.date_analyse.desc())
            .limit(NB_ANALYSES_PAR_FICHE)
            .all()
        )
        lignes = [f"- {Pseudonymes.jeton(cid)} ({_description_client(c)}"
                  f"{', situation : ' + c.situation_familiale if c.situation_familiale else ''})"]
        if not analyses:
            lignes.append("  aucune analyse")
        for a in analyses:
            date = a.date_analyse.strftime("%d/%m/%Y") if a.date_analyse else "date inconnue"
            lignes.append(
                f"  analyse N {a.id} du {date} : decision {a.decision}, risque {a.classe_risque}, "
                f"probabilite de defaut {_pct(a.probabilite_defaut)}, issue reelle {_issue(a.resultat_reel)}"
            )
        blocs.append("\n".join(lignes))
    return "\n".join(blocs)


def _apercu_clients(db: Session, total_clients: int) -> str:
    """Apercu des clients les plus recents avec leur derniere analyse.

    Chargement en 2 requetes au lieu de N+1 : toutes les analyses des clients
    sont recuperees en une fois, puis la plus recente est retenue par client."""
    clients = (
        db.query(models.Client)
        .order_by(models.Client.date_creation.desc(), models.Client.id.desc())
        .limit(NB_CLIENTS_APERCU)
        .all()
    )
    if not clients:
        return "Aucun client enregistre."

    ids = [c.id for c in clients]
    analyses = (
        db.query(models.Analyse)
        .filter(models.Analyse.client_id.in_(ids))
        .order_by(models.Analyse.date_analyse.desc())
        .all()
    )
    derniere_par_client = {}
    for a in analyses:
        if a.client_id not in derniere_par_client:
            derniere_par_client[a.client_id] = a

    titre = "APERCU DES CLIENTS (avec leur derniere analyse)"
    if total_clients > len(clients):
        titre += (f" - seuls les {len(clients)} plus recents sur {total_clients} sont listes ; "
                  "pour un autre client, l'agent doit citer son nom")
    lignes = [titre + " :"]
    for c in clients:
        a = derniere_par_client.get(c.id)
        if a:
            infos = (f"decision {a.decision}, risque {a.classe_risque}, "
                     f"probabilite de defaut {_pct(a.probabilite_defaut)}, "
                     f"issue reelle {_issue(a.resultat_reel)}")
        else:
            infos = "aucune analyse"
        lignes.append(f"- {Pseudonymes.jeton(c.id)} ({_description_client(c)}) : {infos}")
    return "\n".join(lignes)


def _contexte_dossier(db: Session, analyse_id: int) -> str:
    """Contexte detaille d'une analyse precise (pour une question sur un dossier).
    Complete par un rappel des statistiques globales pour permettre les
    comparaisons (ex : 'par rapport a la moyenne')."""
    analyse = db.query(models.Analyse).filter(models.Analyse.id == analyse_id).first()
    if not analyse:
        return None

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

    client = Pseudonymes.jeton(analyse.client_id) if analyse.client_id else "inconnu"
    bloc_dossier = (
        f"DOSSIER ANALYSE N {analyse.id} :\n"
        f"- Client : {client}\n"
        f"- Decision : {analyse.decision}\n"
        f"- Probabilite de defaut : {_pct(analyse.probabilite_defaut)}\n"
        f"- Classe de risque : {analyse.classe_risque}\n"
        f"- Issue reelle : {_issue(analyse.resultat_reel)}\n"
        f"- Explication : {analyse.explication or 'non disponible'}\n"
        f"- Facteurs determinants : {facteurs or 'non disponibles'}"
    )
    return bloc_dossier + "\n\n" + _statistiques(db)


def _contexte_utilisateur(utilisateur) -> str:
    if utilisateur is None:
        return ""
    role = "administrateur" if utilisateur.role == "admin" else "agent de credit"
    return f"UTILISATEUR CONNECTE : {utilisateur.nom} ({role})"


# ---------------------------------------------------------------------------
# Le prompt systeme
# ---------------------------------------------------------------------------
_SEUIL = int(SEUIL_DECISION * 100)
_FAIBLE = int(SEUIL_RISQUE_FAIBLE * 100)

PROMPT_SYSTEME = f"""Tu es CrediBot, l'assistant intelligent de CREDISCORE, l'application de scoring credit de la BSIC Tchad (Banque Sahelo-Saharienne pour l'Investissement et le Commerce).

TON ROLE :
Tu aides les agents de credit et les administrateurs a comprendre les donnees, les analyses de credit et les decisions, et a utiliser l'application. Tu es leur collegue de confiance.

TON CREATEUR :
Si on te demande qui t'a cree, concu ou developpe, reponds que CrediBot a ete concu et developpe par Komhidi Jean Jacques, etudiant a l'UCAO (Universite Catholique de l'Afrique de l'Ouest), dans le cadre de son memoire de master. Precise qu'il a ete cree pour aider les agents de credit de la BSIC a comprendre les analyses de risque et a prendre de meilleures decisions. Ne cite jamais d'autre createur ni l'entreprise qui fournit le modele de langage.

TON COMPORTEMENT :
- Tu es professionnel, precis et fiable, mais aussi chaleureux et accessible.
- Le contexte t'indique l'utilisateur connecte. Au tout premier message d'une conversation, salue-le par son nom ; ensuite, va droit au but, comme dans une vraie discussion.
- Adapte-toi a son role : un agent de credit a besoin de reponses pratiques sur ses dossiers ; un administrateur peut aussi s'interesser au monitoring, a la derive des donnees et au reentrainement du modele.
- Tu reponds de maniere concise et claire. Pas de bavardage inutile.
- Tu bases TOUJOURS tes reponses sur les donnees fournies dans le contexte. Tu n'inventes jamais de chiffres.
- Si une information n'est pas dans le contexte, tu le dis honnetement : "Je n'ai pas cette information dans les donnees actuelles."
- Tu peux mettre en forme tes reponses en Markdown (listes avec des tirets, gras avec **, titres avec ##, tableaux Markdown) pour plus de clarte.
- REGLE ABSOLUE SUR LE HTML : n'utilise JAMAIS de balises HTML, en particulier JAMAIS de <br>, <table>, <div> ou <ul>. L'interface n'affiche pas le HTML.
- REGLE SUR LES TABLEAUX : n'utilise un tableau Markdown QUE lorsque chaque cellule tient en une seule ligne courte. Sinon, structure ta reponse en sections avec des puces "- ". Ne mets jamais de <br> ni de puces dans une cellule.

CONFIDENTIALITE DES CLIENTS :
Les clients sont designes par un identifiant de la forme Client#12. Ecris TOUJOURS cet identifiant exactement sous cette forme (Client# suivi du numero, sans espace) pour parler d'un client : l'interface le remplace automatiquement par son vrai nom. N'essaie jamais de deviner ou d'inventer le nom d'un client.

TON EXPERTISE (seuils reels du modele) :
- La probabilite de defaut est estimee par un modele de machine learning (Gradient Boosting), et chaque decision est expliquee par ses principaux facteurs (methode SHAP).
- Classes de risque : faible si la probabilite de defaut est inferieure a {_FAIBLE} %, moyen entre {_FAIBLE} % et {_SEUIL} %, eleve a partir de {_SEUIL} %.
- Decision : le credit est REFUSE quand la probabilite de defaut atteint ou depasse {_SEUIL} % ; en dessous, il est ACCORDE. Un dossier a risque moyen est donc accorde.
- L'issue reelle : une fois un credit suivi, l'agent indique s'il a ete rembourse ou s'il a fait defaut. Cela mesure si les predictions etaient justes et enrichit les donnees du prochain reentrainement.

GUIDE DE L'APPLICATION CREDISCORE (menu de gauche) :
- Tableau de bord : statistiques generales (credits accordes ou refuses, repartition du risque, analyses des 7 derniers jours, dernieres analyses).
- Analyse de credit : rechercher le client par son nom, remplir le formulaire du dossier (age, revenus, montant du credit, echeance, prix du bien, profession, etc.), lancer l'analyse. Le resultat affiche la probabilite de defaut, la decision, les facteurs explicatifs et un bouton pour telecharger la fiche de decision en PDF.
- Clients : liste et recherche des clients ; bouton "Nouveau client" pour en creer un (nom complet, genre, age, profession, situation familiale) ; modification depuis la liste. La suppression d'un client est reservee a l'administrateur.
- Historique : toutes les analyses realisees, avec le telechargement du PDF de chaque fiche et l'acces au detail. Dans le detail d'une analyse, l'agent peut renseigner le resultat reel du credit (rembourse ou defaut).
- Notifications : alertes de l'application (par exemple la fin d'un reentrainement).
- Assistant IA : c'est toi, CrediBot ; chaque conversation est enregistree et peut etre reprise ou supprimee.
- Mon profil : informations personnelles, activite, et changement du mot de passe.
- Reserve a l'administrateur : "Utilisateurs" (creer, modifier, supprimer les comptes des agents) et "Monitoring" (performances du modele, derive des donnees, bouton "Reentrainer le modele").
Si on te demande comment faire quelque chose dans l'application, appuie-toi sur ce guide.

Reponds toujours en francais, de maniere naturelle et utile."""


# ---------------------------------------------------------------------------
# Reponse a une question
# ---------------------------------------------------------------------------
def construire_contexte(db: Session, ps: Pseudonymes, question: str,
                        analyse_id: int = None, historique: list = None,
                        utilisateur=None):
    """Construit le contexte (deja pseudonymise) envoye au modele.
    Renvoie None si l'analyse demandee n'existe pas."""
    if analyse_id is not None:
        contexte = _contexte_dossier(db, analyse_id)
        if contexte is None:
            return None
    else:
        # Clients cites : dans la question, ou dans les derniers messages de
        # l'agent (pour les relances du type "et son dernier credit ?")
        textes = [question] + [
            m.get("contenu", "") for m in (historique or [])[-4:] if m.get("role") != "assistant"
        ]
        cites = []
        for texte in textes:
            for cid in ps.clients_cites(texte):
                if cid not in cites:
                    cites.append(cid)
        total_clients = db.query(models.Client).count()
        morceaux = [_statistiques(db), _fiches_clients(db, cites[:NB_FICHES_MAX]),
                    _apercu_clients(db, total_clients)]
        contexte = "\n\n".join(m for m in morceaux if m)

    utilisateur_txt = _contexte_utilisateur(utilisateur)
    if utilisateur_txt:
        contexte = utilisateur_txt + "\n\n" + contexte
    return contexte


def repondre(db: Session, question: str, analyse_id: int = None,
             historique: list = None, utilisateur=None) -> str:
    """Repond a une question de l'agent, avec un contexte riche et le contexte
    de la conversation en cours. Aucun nom de client n'est envoye a Groq."""
    if client_groq is None:
        return "L'assistant n'est pas configure : la cle GROQ_API_KEY est absente."

    ps = Pseudonymes(db.query(models.Client.id, models.Client.nom).all())
    contexte = construire_contexte(db, ps, question, analyse_id, historique, utilisateur)
    if contexte is None:
        return f"Je ne trouve pas l'analyse N {analyse_id}."

    try:
        liste_messages = [
            {"role": "system", "content": PROMPT_SYSTEME + "\n\nCONTEXTE ACTUEL DES DONNEES :\n" + contexte},
        ]
        # On ne garde que les derniers echanges pour limiter la latence et les tokens.
        for msg in (historique or [])[-MAX_HISTORIQUE:]:
            role = "assistant" if msg.get("role") == "assistant" else "user"
            contenu = msg.get("contenu", "")
            if contenu:
                liste_messages.append({"role": role, "content": ps.masquer(contenu)})
        liste_messages.append({"role": "user", "content": ps.masquer(question)})

        reponse = client_groq.chat.completions.create(
            model=MODELE_LLM,
            messages=liste_messages,
            temperature=0.4,
            max_tokens=1000,
        )
        texte = reponse.choices[0].message.content.strip()
        return _nettoyer_html(ps.demasquer(texte))
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

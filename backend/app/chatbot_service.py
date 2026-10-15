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

# Liste des clients envoyee a chaque question (une ligne courte par client).
# Au-dela, seuls les plus recents sont listes ; les clients cites par leur nom
# sont TOUJOURS ajoutes en plus, et le classement porte sur TOUS les clients.
NB_CLIENTS_APERCU = 200
# Nombre maximal de fiches detaillees (clients cites) par question.
NB_FICHES_MAX = 5
# Nombre d'analyses detaillees par fiche client (historique).
NB_ANALYSES_PAR_FICHE = 20
# Nombre de clients dans chaque classement (plus dangereux / plus stables).
NB_CLASSEMENT = 3


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


def _date(a) -> str:
    return a.date_analyse.strftime("%d/%m/%Y") if a.date_analyse else "date inconnue"


def _analyses_par_client(db: Session) -> dict:
    """Toutes les analyses, regroupees par client, de la plus recente a la
    plus ancienne (une seule requete pour tous les clients)."""
    analyses = (
        db.query(models.Analyse)
        .filter(models.Analyse.client_id.isnot(None))
        .order_by(models.Analyse.date_analyse.desc(), models.Analyse.id.desc())
        .all()
    )
    par_client = {}
    for a in analyses:
        par_client.setdefault(a.client_id, []).append(a)
    return par_client


def _tendance(analyses: list) -> str:
    """Evolution du risque entre la premiere et la derniere analyse."""
    if len(analyses) < 2:
        return ""
    ecart = (analyses[0].probabilite_defaut or 0) - (analyses[-1].probabilite_defaut or 0)
    if abs(ecart) < 0.02:
        return "  tendance : risque stable"
    sens = "en hausse" if ecart > 0 else "en baisse"
    return (f"  tendance : risque {sens} ({_pct(analyses[-1].probabilite_defaut)} a la premiere "
            f"analyse, {_pct(analyses[0].probabilite_defaut)} a la derniere)")


def _fiches_clients(db: Session, ids: list, par_client: dict) -> str:
    """Fiches detaillees (historique complet) des clients cites dans la question."""
    if not ids:
        return ""
    clients = {c.id: c for c in db.query(models.Client).filter(models.Client.id.in_(ids)).all()}
    blocs = ["FICHES DES CLIENTS CITES DANS LA QUESTION (historique, de la plus recente a la plus ancienne) :"]
    for cid in ids:
        c = clients.get(cid)
        if not c:
            continue
        toutes = par_client.get(cid, [])
        analyses = toutes[:NB_ANALYSES_PAR_FICHE]
        lignes = [f"- {Pseudonymes.jeton(cid)} ({_description_client(c)}"
                  f"{', situation : ' + c.situation_familiale if c.situation_familiale else ''})"
                  f" : {len(toutes)} analyse(s)"]
        if not analyses:
            lignes.append("  aucune analyse")
        for a in analyses:
            lignes.append(
                f"  analyse N {a.id} du {_date(a)} : decision {a.decision}, risque {a.classe_risque}, "
                f"probabilite de defaut {_pct(a.probabilite_defaut)}, issue reelle {_issue(a.resultat_reel)}"
            )
        if len(toutes) > len(analyses):
            lignes.append(f"  ... et {len(toutes) - len(analyses)} analyse(s) plus ancienne(s)")
        tendance = _tendance(analyses)
        if tendance:
            lignes.append(tendance)
        blocs.append("\n".join(lignes))
    return "\n".join(blocs)


def _a_fait_defaut(analyses: list) -> bool:
    return any(_normaliser(a.resultat_reel).startswith("defaut") for a in analyses)


def _classement(par_client: dict) -> str:
    """Classement des clients les plus dangereux et les plus stables, calcule
    sur TOUS les clients avec des regles fixes (le chatbot ne fait que le
    commenter, il ne devine rien).

    - Plus dangereux : probabilite de defaut de la DERNIERE analyse la plus
      elevee ; a egalite, un client ayant deja fait defaut passe devant.
    - Plus stable : parmi les clients sans aucun defaut reel et dont toutes
      les analyses ont ete accordees, ceux suivis au moins 2 fois passent
      devant ; puis probabilite de defaut de la derniere analyse la plus basse.
    """
    if not par_client:
        return ""

    def ligne(cid, analyses):
        derniere = analyses[0]
        extra = ", a deja fait DEFAUT" if _a_fait_defaut(analyses) else ""
        return (f"- {Pseudonymes.jeton(cid)} : derniere analyse N {derniere.id} du {_date(derniere)}, "
                f"probabilite de defaut {_pct(derniere.probabilite_defaut)}, "
                f"decision {derniere.decision}, {len(analyses)} analyse(s){extra}")

    dangereux = sorted(
        par_client.items(),
        key=lambda x: (-(x[1][0].probabilite_defaut or 0), not _a_fait_defaut(x[1])),
    )[:NB_CLASSEMENT]

    candidats_stables = [
        (cid, an) for cid, an in par_client.items()
        if not _a_fait_defaut(an) and all(_normaliser(a.decision).startswith("accord") for a in an)
    ]
    stables = sorted(
        candidats_stables,
        key=lambda x: (0 if len(x[1]) >= 2 else 1, x[1][0].probabilite_defaut or 0),
    )[:NB_CLASSEMENT]

    lignes = [
        "CLASSEMENT DES CLIENTS (calcule sur tous les clients) :",
        "Les plus dangereux (probabilite de defaut de la derniere analyse la plus elevee ; "
        "a egalite, un defaut reel passe devant) :",
    ]
    lignes += [ligne(cid, an) for cid, an in dangereux]
    lignes.append("Les plus stables (aucun defaut reel, toutes les analyses accordees ; "
                  "clients suivis au moins 2 fois en priorite, puis probabilite la plus basse) :")
    if stables:
        lignes += [ligne(cid, an) for cid, an in stables]
    else:
        lignes.append("- aucun client ne remplit ces conditions pour l'instant")
    return "\n".join(lignes)


def _liste_clients(db: Session, total_clients: int, par_client: dict) -> str:
    """Liste des clients (les plus recents d'abord) avec leur derniere analyse."""
    clients = (
        db.query(models.Client)
        .order_by(models.Client.date_creation.desc(), models.Client.id.desc())
        .limit(NB_CLIENTS_APERCU)
        .all()
    )
    if not clients:
        return "Aucun client enregistre."

    titre = f"LISTE DES CLIENTS ({total_clients} au total, avec leur derniere analyse)"
    if total_clients > len(clients):
        titre += (f" - seuls les {len(clients)} plus recents sont listes ; "
                  "pour un autre client, l'agent doit citer son nom")
    lignes = [titre + " :"]
    for c in clients:
        analyses = par_client.get(c.id, [])
        if analyses:
            a = analyses[0]
            infos = (f"{len(analyses)} analyse(s), derniere : N {a.id} du {_date(a)}, "
                     f"decision {a.decision}, risque {a.classe_risque}, "
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

LISTES, HISTORIQUES ET CLASSEMENTS :
- Pour lister des clients (tous, ou filtres par decision, par niveau de risque ou par issue reelle), appuie-toi sur la LISTE DES CLIENTS du contexte. Indique le nombre de clients concernes. Si la liste est longue, presente-la de facon compacte (une ligne par client).
- Pour l'historique d'un client, appuie-toi sur sa FICHE : presente ses analyses dans l'ordre chronologique et commente la tendance de son risque.
- Pour le client le plus dangereux ou le plus stable, utilise UNIQUEMENT le CLASSEMENT DES CLIENTS du contexte, et explique en une phrase la regle utilisee. Ne refais jamais ce classement toi-meme.

FICHE PDF A TELECHARGER :
L'interface sait afficher un bouton de telechargement de la fiche de decision PDF d'une analyse. Pour le faire apparaitre, ecris sur une ligne seule, a la fin de ta reponse : [PDF:numero] (exemple : [PDF:42]), avec le numero d'une analyse presente dans le contexte.
- Mets-le quand on te demande une fiche, un PDF, un document ou un rapport sur un client ou une analyse. Pour un client, utilise sa DERNIERE analyse.
- Tu peux aussi le proposer quand tu presentes le client le plus dangereux ou le plus stable.
- Maximum 3 boutons par reponse. N'invente jamais de numero d'analyse ; si le client n'a aucune analyse, dis qu'il n'y a pas encore de fiche.
- Ne dis pas que tu "envoies" un fichier : dis que la fiche est disponible au telechargement ci-dessous.

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
        par_client = _analyses_par_client(db)
        morceaux = [_statistiques(db),
                    _classement(par_client),
                    _fiches_clients(db, cites[:NB_FICHES_MAX], par_client),
                    _liste_clients(db, total_clients, par_client)]
        contexte = "\n\n".join(m for m in morceaux if m)

    utilisateur_txt = _contexte_utilisateur(utilisateur)
    if utilisateur_txt:
        contexte = utilisateur_txt + "\n\n" + contexte
    return contexte


def preparer_requete(db: Session, question: str, analyse_id: int = None,
                     historique: list = None, utilisateur=None):
    """Prepare les messages a envoyer a Groq (deja pseudonymises).

    Renvoie (messages, pseudonymes, None) si tout va bien, ou
    (None, None, message_d_erreur) si la question ne peut pas etre traitee."""
    if client_groq is None:
        return None, None, "L'assistant n'est pas configure : la cle GROQ_API_KEY est absente."

    ps = Pseudonymes(db.query(models.Client.id, models.Client.nom).all())
    contexte = construire_contexte(db, ps, question, analyse_id, historique, utilisateur)
    if contexte is None:
        return None, None, f"Je ne trouve pas l'analyse N {analyse_id}."

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
    return liste_messages, ps, None


def _message_erreur(e: Exception) -> str:
    """Traduit une erreur Groq en message comprehensible pour l'agent."""
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


def repondre(db: Session, question: str, analyse_id: int = None,
             historique: list = None, utilisateur=None) -> str:
    """Repond a une question de l'agent (reponse complete en une fois).
    Aucun nom de client n'est envoye a Groq."""
    liste_messages, ps, erreur = preparer_requete(db, question, analyse_id, historique, utilisateur)
    if erreur:
        return erreur
    try:
        reponse = client_groq.chat.completions.create(
            model=MODELE_LLM,
            messages=liste_messages,
            temperature=0.4,
            max_tokens=1000,
        )
        texte = reponse.choices[0].message.content.strip()
        return _nettoyer_html(ps.demasquer(texte))
    except Exception as e:
        return _message_erreur(e)


# ---------------------------------------------------------------------------
# Reponse progressive (streaming)
# ---------------------------------------------------------------------------
class DemasqueurFlux:
    """Retablit les vrais noms dans une reponse qui arrive par petits morceaux.

    Un identifiant comme 'Client#12' peut etre coupe entre deux morceaux
    ('Cli' puis 'ent#12'). On garde donc en attente la fin du texte tant
    qu'elle pourrait etre le debut d'un identifiant (ou d'une balise HTML a
    nettoyer), et on ne l'envoie qu'une fois sure."""

    # Fin de texte qui POURRAIT etre un identifiant inacheve : 'C', 'Cli',
    # 'Client', 'Client#', 'Client#1' (d'autres chiffres peuvent suivre)...
    _DEBUT_JETON = re.compile(
        r"C(?:l(?:i(?:e(?:n(?:t(?:\s*(?:#\s*\d*)?)?)?)?)?)?)?$", re.IGNORECASE)
    # Balise HTML commencee mais pas encore fermee
    _DEBUT_BALISE = re.compile(r"<[^>]{0,15}$")

    def __init__(self, pseudonymes: Pseudonymes):
        self.ps = pseudonymes
        self.attente = ""

    def ajouter(self, morceau: str) -> str:
        """Ajoute un morceau recu ; renvoie le texte sur, pret a afficher."""
        texte = self.attente + morceau
        coupure = len(texte)
        for motif in (self._DEBUT_JETON, self._DEBUT_BALISE):
            m = motif.search(texte)
            if m:
                coupure = min(coupure, m.start())
        self.attente = texte[coupure:]
        return self._propre(texte[:coupure])

    def terminer(self) -> str:
        """Fin du flux : renvoie ce qui restait en attente."""
        reste, self.attente = self.attente, ""
        return self._propre(reste)

    def _propre(self, texte: str) -> str:
        if not texte:
            return ""
        texte = self.ps.demasquer(texte)
        texte = re.sub(r"<\s*br\s*/?\s*>", "\n", texte, flags=re.IGNORECASE)
        return re.sub(r"</?\s*(div|span|table|tr|td|th|ul|ol|li)[^>]*>", "", texte, flags=re.IGNORECASE)


def repondre_en_flux(liste_messages: list, ps: Pseudonymes):
    """Generateur : renvoie la reponse de Groq morceau par morceau, avec les
    vrais noms des clients deja retablis. En cas d'erreur, renvoie le message
    d'erreur comme dernier morceau."""
    demasqueur = DemasqueurFlux(ps)
    try:
        flux = client_groq.chat.completions.create(
            model=MODELE_LLM,
            messages=liste_messages,
            temperature=0.4,
            max_tokens=1000,
            stream=True,
        )
        for evenement in flux:
            if not evenement.choices:
                continue
            morceau = evenement.choices[0].delta.content
            if morceau:
                sortie = demasqueur.ajouter(morceau)
                if sortie:
                    yield sortie
        fin = demasqueur.terminer()
        if fin:
            yield fin
    except Exception as e:
        fin = demasqueur.terminer()
        if fin:
            yield fin
        yield ("\n\n" if fin else "") + _message_erreur(e)

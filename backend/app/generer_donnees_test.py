# -*- coding: utf-8 -*-
"""
Generation de donnees de test pour CREDISCORE.

Remplit la base avec des donnees fictives mais realistes pour tester et
presenter toute l'application :
- 2 agents de credit (en plus de l'administrateur existant) ;
- 30 clients, dont plusieurs suivis sur plusieurs analyses (historique) ;
- environ 150 analyses reparties sur 6 mois, calculees par le vrai modele
  (probabilite, decision, facteurs SHAP, explication), avec des montants dans
  les 4 tranches du tableau de bord ;
- l'issue reelle (rembourse / defaut) d'une partie des credits anciens, le
  reste apparaissant dans "Dossiers a suivre" ;
- deux clients "vitrines" pour CrediBot : un client tres stable et un client
  dont le risque augmente ;
- une derive volontaire, pour montrer le monitoring : sur les 30 derniers jours,
  les demandeurs gagnent moins et empruntent plus (derive des donnees), et les
  credits accordes il y a 1 a 4 mois font plus souvent defaut que prevu
  (derive de concept). Option --sans-derive pour des donnees stables.

Utilisation, depuis le dossier backend (une base deja initialisee, avec un
administrateur cree par app.creer_admin) :
    python -m app.generer_donnees_test            # refuse si la base contient deja des analyses
    python -m app.generer_donnees_test --ajouter  # ajoute quand meme
    python -m app.generer_donnees_test --sans-derive   # donnees stables, sans alerte

Attention : donnees fictives. A ne jamais lancer sur une base de production reelle.
"""

import sys
import json
import random
from datetime import datetime, timedelta

from .database import SessionLocal
from . import models
from .model_service import ServiceModele
from .security import hacher_mot_de_passe
from .alertes_service import alerter_client_en_hausse

random.seed(2026)

NB_ANALYSES = 240
PART_RECENTE = 0.45      # part des analyses sur les 30 derniers jours
JOURS_HISTORIQUE = 180
MOT_DE_PASSE_AGENTS = "Agent@2026"
AGENTS = [("Fatimé Abakar", "fatime.abakar@bsic.td"), ("Moussa Ngarlem", "moussa.ngarlem@bsic.td")]

NOMS = [
    "Kadidja Moussa", "Ahmat Djibrine", "Fatime Hassan", "Youssouf Ali", "Mariam Abakar",
    "Idriss Mahamat", "Zara Oumar", "Brahim Saleh", "Achta Nour", "Hassan Adam",
    "Amina Tahir", "Halimé Youssouf", "Abakar Issa", "Ngarta Bekri", "Hawa Djibrine",
    "Djimet Allamine", "Ramatou Seid", "Saleh Ahmat", "Khadidja Brahim", "Ousmane Kaya",
    "Mahamat Nour", "Hissein Abdel", "Asta Mahamat", "Rakhié Ali", "Adoum Hassane",
    "Nadjiyo Remadji", "Clément Ngaba", "Esther Neldé",
]
# Prenoms feminins (le genre du client suit son prenom)
PRENOMS_FEMININS = {"Kadidja", "Fatime", "Mariam", "Zara", "Achta", "Amina", "Halimé", "Hawa",
                    "Ramatou", "Khadidja", "Asta", "Rakhié", "Nadjiyo", "Esther"}
CLIENT_STABLE = "Ali Mahamat Saleh"      # plusieurs credits, tous rembourses
CLIENT_RISQUE = "Achta Oumar Abdoulaye"  # risque en hausse, dernier dossier refuse

PROFESSIONS = ["Enseignant", "Commerçant", "Fonctionnaire", "Infirmier", "Comptable",
               "Chauffeur", "Agriculteur", "Éleveur", "Artisan"]
SITUATIONS = ["Married", "Single / not married", "Civil marriage", "Widow", "Separated"]
OCCUPATIONS = ["Core staff", "Laborers", "Managers", "Drivers", "Sales staff", "Accountants"]
EMPLOYEURS = ["School", "Government", "Business Entity Type 3", "Self-employed", "Medicine", "Trade: type 7"]

# Tranches de montant (FCFA) et leur poids : beaucoup de petits credits, peu de gros
TRANCHES = [((300_000, 990_000), 0.30), ((1_000_000, 2_990_000), 0.35),
            ((3_000_000, 4_990_000), 0.20), ((5_000_000, 12_000_000), 0.15)]
# Derive : les demandes recentes portent sur des montants plus eleves
TRANCHES_DERIVE = [((300_000, 990_000), 0.12), ((1_000_000, 2_990_000), 0.28),
                   ((3_000_000, 4_990_000), 0.28), ((5_000_000, 12_000_000), 0.32)]


def _montant(tranches=TRANCHES):
    r, cumul = random.random(), 0
    for (bas, haut), poids in tranches:
        cumul += poids
        if r <= cumul:
            return round(random.randint(bas, haut), -4)
    return 2_000_000


def genre_de(nom: str) -> str:
    return "F" if nom.split()[0] in PRENOMS_FEMININS else "M"


def dossier(qualite: float, montant: int = None, age: int = None, genre: str = None,
            situation: str = None, tension: float = 0.0) -> dict:
    """Dossier de credit. qualite : 0 (tres risque) a 1 (tres solide)."""
    montant = montant or _montant()
    duree = random.choice([12, 18, 24, 36, 48, 60])
    ext = lambda: round(min(max(random.gauss(0.15 + 0.6 * qualite, 0.1), 0.02), 0.95), 2)
    echeance = round(montant / duree * random.uniform(1.05, 1.2), -3)
    # Revenu deduit d'un taux d'endettement realiste (environ 20 % a 70 %)
    # tension > 0 : demandeurs plus endettes, donc revenus plus faibles (derive)
    endettement = min(max(random.gauss(0.45 - 0.25 * qualite + tension, 0.08), 0.15), 0.85)
    revenu = max(round(echeance / endettement, -3), 60_000)
    return {
        "AGE_ANNEES": age or random.randint(23, 60),
        "CODE_GENDER": genre or random.choice(["M", "F"]),
        "NAME_FAMILY_STATUS": situation or random.choice(SITUATIONS),
        "CNT_CHILDREN": random.randint(0, 5),
        "CNT_FAM_MEMBERS": random.randint(1, 8),
        "NAME_EDUCATION_TYPE": random.choice(["Higher education", "Secondary / secondary special",
                                              "Lower secondary"]),
        "OCCUPATION_TYPE": random.choice(OCCUPATIONS),
        "ORGANIZATION_TYPE": random.choice(EMPLOYEURS),
        "NAME_INCOME_TYPE": random.choice(["Working", "Commercial associate", "State servant"]),
        "ANCIENNETE_EMPLOI_ANNEES": round(max(0.5, random.gauss(2 + 12 * qualite, 3)), 1),
        "EMPLOI_ANORMAL": 0,
        "AMT_INCOME_TOTAL": revenu,
        "AMT_CREDIT": montant,
        "AMT_ANNUITY": echeance,
        "AMT_GOODS_PRICE": round(montant * random.uniform(0.9, 1.0), -4),
        "NAME_CONTRACT_TYPE": random.choice(["Cash loans", "Cash loans", "Revolving loans"]),
        "EXT_SOURCE_1": ext(), "EXT_SOURCE_2": ext(), "EXT_SOURCE_3": ext(),
    }


def dossier_cible(service, pmin, pmax, **kw):
    """Dossier dont la probabilite de defaut tombe entre pmin et pmax
    (pour des clients vitrines a l'evolution lisible)."""
    for _ in range(400):
        q = random.uniform(0, 1)
        d = dossier(q, **kw)
        if pmin <= service.predire(d) < pmax:
            return d
    return d


def _date(jours_min, jours_max):
    jours = random.randint(jours_min, jours_max)
    return datetime.utcnow() - timedelta(days=jours, hours=random.randint(0, 9), minutes=random.randint(0, 59))


def _issue(analyse, rembourse_force=None, concept=False):
    """Issue reelle d'un credit accorde, correlee a la probabilite de defaut.

    concept=True : derive de concept, le lien entre le score et le defaut
    s'affaiblit et le defaut augmente (le modele sous-estime le risque)."""
    if rembourse_force is not None:
        return "rembourse" if rembourse_force else "defaut"
    p = analyse.probabilite_defaut
    risque = 0.30 + 0.25 * p if concept else p * 0.8
    return "defaut" if random.random() < risque else "rembourse"


def generer(ajouter=False, derive=True):
    db = SessionLocal()
    try:
        admin = db.query(models.User).filter(models.User.role == "admin").first()
        if not admin:
            print("Aucun administrateur. Lancez d'abord : python -m app.creer_admin")
            return
        deja = db.query(models.Analyse).count()
        if deja and not ajouter:
            print(f"La base contient deja {deja} analyses. Relancez avec --ajouter pour completer quand meme.")
            return

        service = ServiceModele()
        version = db.query(models.ModelVersion).filter(models.ModelVersion.en_production == True).first()
        if not version:
            version = models.ModelVersion(algorithme="Gradient Boosting", auc=0.753, en_production=True)
            db.add(version)
            db.commit()
            db.refresh(version)

        # Agents de credit
        utilisateurs = [admin]
        for nom, email in AGENTS:
            agent = db.query(models.User).filter(models.User.email == email).first()
            if not agent:
                agent = models.User(nom=nom, email=email, role="agent",
                                    mot_de_passe=hacher_mot_de_passe(MOT_DE_PASSE_AGENTS))
                db.add(agent)
                db.commit()
                db.refresh(agent)
            utilisateurs.append(agent)

        # Clients
        clients = {}
        for nom in NOMS + [CLIENT_STABLE, CLIENT_RISQUE]:
            c = models.Client(nom=nom, genre=genre_de(nom), age=random.randint(23, 62),
                              profession=random.choice(PROFESSIONS),
                              situation_familiale=random.choice(SITUATIONS))
            db.add(c)
            clients[nom] = c
        clients[CLIENT_STABLE].age = 42
        clients[CLIENT_STABLE].profession = "Fonctionnaire"
        clients[CLIENT_RISQUE].age = 26
        clients[CLIENT_RISQUE].profession = "Commerçante"
        db.commit()

        def profil(client):
            """Age, genre et situation du dossier : ceux du client."""
            return {"age": int(client.age), "genre": client.genre, "situation": client.situation_familiale}

        def enregistrer(client, d, date, utilisateur, issue=None):
            r = service.analyser(d)
            a = models.Analyse(
                probabilite_defaut=r["probabilite_defaut"], classe_risque=r["classe_risque"],
                decision=r["decision"],
                facteurs_explicatifs=json.dumps(r["facteurs_explicatifs"], ensure_ascii=False),
                explication=r.get("explication", ""), donnees_dossier=json.dumps(d, ensure_ascii=False),
                date_analyse=date, client_id=client.id, user_id=utilisateur.id,
                model_version_id=version.id)
            if issue is not None and a.decision == "ACCORDE":
                a.resultat_reel = issue(a)
            db.add(a)
            return a

        # Clients vitrines (pour CrediBot et l'historique)
        stable = [(170, 1_500_000, .14, .20), (110, 2_000_000, .12, .18), (50, 2_500_000, .10, .16), (3, 3_000_000, .08, .14)]
        for i, (jours, montant, pmin, pmax) in enumerate(stable):
            issue = (lambda a: _issue(a, rembourse_force=True)) if jours > 30 else None
            enregistrer(clients[CLIENT_STABLE], dossier_cible(service, pmin, pmax, montant=montant, **profil(clients[CLIENT_STABLE])),
                        _date(jours, jours), admin if i < 3 else utilisateurs[1], issue=issue)
        risque = [(120, 800_000, .15, .25), (60, 2_000_000, .35, .45), (20, 4_000_000, .55, .65), (2, 9_000_000, .80, .90)]
        for i, (jours, montant, pmin, pmax) in enumerate(risque):
            issue = (lambda a: _issue(a, rembourse_force=True)) if i == 0 else None
            derniere = enregistrer(clients[CLIENT_RISQUE], dossier_cible(service, pmin, pmax, montant=montant, **profil(clients[CLIENT_RISQUE])),
                        _date(jours, jours), utilisateurs[2], issue=issue)

        # L'agent du client en hausse recoit l'alerte, comme lors d'une vraie analyse
        db.flush()
        alerter_client_en_hausse(db, derniere)

        # Analyses courantes : 60 % sur le dernier mois, le reste sur 6 mois
        autres = [clients[n] for n in NOMS]
        for _ in range(NB_ANALYSES - 7):
            date = _date(0, 29) if random.random() < PART_RECENTE else _date(30, JOURS_HISTORIQUE)
            anciennete = (datetime.utcnow() - date).days
            recent = anciennete < 30 and derive
            # Issue connue pour environ 85 % des credits accordes depuis plus de 30 jours ;
            # derive de concept sur les credits accordes il y a 1 a 4 mois
            issue = None
            if anciennete > 30 and random.random() < 0.85:
                concept = derive and anciennete <= 120
                issue = (lambda a, c=concept: _issue(a, concept=c))
            montant = _montant(TRANCHES_DERIVE if recent else TRANCHES)
            # Les gros montants sont un peu plus risques, comme en pratique
            qualite = random.betavariate(1.15, 1.6) - (0.12 if montant >= 5_000_000 else 0.05 if montant >= 3_000_000 else 0)
            if recent:
                qualite -= 0.08
            client = random.choice(autres)
            enregistrer(client, dossier(max(qualite, 0), montant=montant, tension=0.12 if recent else 0.0,
                                        **profil(client)), date, random.choice(utilisateurs), issue=issue)
        db.commit()

        total = db.query(models.Analyse).count()
        accordes = db.query(models.Analyse).filter(models.Analyse.decision == "ACCORDE").count()
        issues = db.query(models.Analyse).filter(models.Analyse.resultat_reel.isnot(None)).count()
        print(f"{len(clients)} clients et {NB_ANALYSES} analyses crees ({total} au total en base).")
        print(f"Credits accordes : {accordes} ; issues reelles renseignees : {issues}.")
        print("Comptes agents (mot de passe : " + MOT_DE_PASSE_AGENTS + ") : "
              + ", ".join(email for _, email in AGENTS))
        print(f"Clients vitrines pour CrediBot : {CLIENT_STABLE} (stable), {CLIENT_RISQUE} (risque en hausse).")
    finally:
        db.close()


if __name__ == "__main__":
    generer(ajouter="--ajouter" in sys.argv, derive="--sans-derive" not in sys.argv)

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
  dont le risque augmente.

Utilisation, depuis le dossier backend (une base deja initialisee, avec un
administrateur cree par app.creer_admin) :
    python -m app.generer_donnees_test            # refuse si la base contient deja des analyses
    python -m app.generer_donnees_test --ajouter  # ajoute quand meme

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

random.seed(2026)

NB_ANALYSES = 150
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


def _montant():
    r, cumul = random.random(), 0
    for (bas, haut), poids in TRANCHES:
        cumul += poids
        if r <= cumul:
            return round(random.randint(bas, haut), -4)
    return 2_000_000


def dossier(qualite: float, montant: int = None, age: int = None) -> dict:
    """Dossier de credit. qualite : 0 (tres risque) a 1 (tres solide)."""
    montant = montant or _montant()
    duree = random.choice([12, 18, 24, 36, 48, 60])
    ext = lambda: round(min(max(random.gauss(0.15 + 0.6 * qualite, 0.1), 0.02), 0.95), 2)
    revenu = round(random.randint(80_000, 250_000) + qualite * random.randint(100_000, 500_000), -3)
    return {
        "AGE_ANNEES": age or random.randint(23, 60),
        "CODE_GENDER": random.choice(["M", "F"]),
        "NAME_FAMILY_STATUS": random.choice(SITUATIONS),
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
        "AMT_ANNUITY": round(montant / duree * random.uniform(1.05, 1.2), -3),
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


def _issue(analyse, rembourse_force=None):
    """Issue reelle d'un credit accorde, correlee a la probabilite de defaut."""
    if rembourse_force is not None:
        return "rembourse" if rembourse_force else "defaut"
    return "defaut" if random.random() < analyse.probabilite_defaut * 0.8 else "rembourse"


def generer(ajouter=False):
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
            c = models.Client(nom=nom, genre=random.choice(["M", "F"]), age=random.randint(23, 62),
                              profession=random.choice(PROFESSIONS),
                              situation_familiale=random.choice(SITUATIONS))
            db.add(c)
            clients[nom] = c
        clients[CLIENT_STABLE].genre, clients[CLIENT_STABLE].age = "M", 42
        clients[CLIENT_STABLE].profession = "Fonctionnaire"
        clients[CLIENT_RISQUE].genre, clients[CLIENT_RISQUE].age = "F", 26
        clients[CLIENT_RISQUE].profession = "Commerçante"
        db.commit()

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
            enregistrer(clients[CLIENT_STABLE], dossier_cible(service, pmin, pmax, montant=montant, age=42),
                        _date(jours, jours), admin if i < 3 else utilisateurs[1], issue=issue)
        risque = [(120, 800_000, .15, .25), (60, 2_000_000, .35, .45), (20, 4_000_000, .55, .65), (2, 9_000_000, .80, .90)]
        for i, (jours, montant, pmin, pmax) in enumerate(risque):
            issue = (lambda a: _issue(a, rembourse_force=True)) if i == 0 else None
            enregistrer(clients[CLIENT_RISQUE], dossier_cible(service, pmin, pmax, montant=montant, age=26),
                        _date(jours, jours), utilisateurs[2], issue=issue)

        # Analyses courantes : 60 % sur le dernier mois, le reste sur 6 mois
        autres = [clients[n] for n in NOMS]
        for _ in range(NB_ANALYSES - 7):
            date = _date(0, 29) if random.random() < 0.6 else _date(30, JOURS_HISTORIQUE)
            anciennete = (datetime.utcnow() - date).days
            # Issue connue pour environ 60 % des credits accordes depuis plus de 30 jours
            issue = _issue if anciennete > 30 and random.random() < 0.6 else None
            montant = _montant()
            # Les gros montants sont un peu plus risques, comme en pratique
            qualite = random.betavariate(1.3, 1.5) - (0.12 if montant >= 5_000_000 else 0.05 if montant >= 3_000_000 else 0)
            enregistrer(random.choice(autres), dossier(max(qualite, 0), montant=montant), date,
                        random.choice(utilisateurs), issue=issue)
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
    generer(ajouter="--ajouter" in sys.argv)

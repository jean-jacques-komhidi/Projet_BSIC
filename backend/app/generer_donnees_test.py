# -*- coding: utf-8 -*-
"""
Generation de donnees de test pour CREDISCORE.

Ce script remplit la base avec des clients et des analyses variees, reparties
sur les dernieres semaines, pour disposer de donnees realistes lors des tests
et des demonstrations (tableau de bord, historique, tendances, graphiques).

A lancer une seule fois, depuis le dossier backend :
    python -m app.generer_donnees_test

Attention : cree des donnees fictives. A ne pas utiliser en production.
"""

import json
import random
from datetime import datetime, timedelta

from .database import SessionLocal
from . import models
from .model_service import ServiceModele

random.seed(42)

# Quelques noms tchadiens pour les clients fictifs
NOMS = [
    "Kadidja Moussa", "Ahmat Djibrine", "Fatime Hassan", "Youssouf Ali",
    "Mariam Abakar", "Idriss Mahamat", "Zara Oumar", "Brahim Saleh",
    "Achta Nour", "Hassan Adam", "Amina Tahir", "Oumar Deby",
    "Halime Youssouf", "Abakar Issa", "Ngarta Bekri",
]
PROFESSIONS = ["Enseignant", "Commercant", "Fonctionnaire", "Manoeuvre",
               "Infirmier", "Comptable", "Chauffeur", "Agriculteur"]
SITUATIONS = ["Married", "Single / not married", "Widow", "Separated"]


def dossier_aleatoire():
    """Genere un dossier de credit aleatoire (profil variable)."""
    # Profil bon ou mauvais aleatoirement
    bon = random.random() > 0.4
    if bon:
        ext = [round(random.uniform(0.5, 0.8), 2) for _ in range(3)]
        revenu = random.randint(250000, 600000)
        credit = random.randint(800000, 2500000)
    else:
        ext = [round(random.uniform(0.05, 0.35), 2) for _ in range(3)]
        revenu = random.randint(80000, 200000)
        credit = random.randint(3000000, 6000000)
    age = random.randint(23, 60)
    return {
        "AGE_ANNEES": age, "CODE_GENDER": random.choice(["M", "F"]),
        "NAME_FAMILY_STATUS": random.choice(SITUATIONS),
        "CNT_CHILDREN": random.randint(0, 4),
        "CNT_FAM_MEMBERS": random.randint(1, 6),
        "NAME_EDUCATION_TYPE": random.choice(
            ["Higher education", "Secondary / secondary special"]),
        "OCCUPATION_TYPE": random.choice(["Core staff", "Laborers", "Managers", "Drivers"]),
        "ORGANIZATION_TYPE": random.choice(["School", "Government", "Business Entity Type 3", "Self-employed"]),
        "NAME_INCOME_TYPE": "Working",
        "ANCIENNETE_EMPLOI_ANNEES": random.randint(1, 20),
        "EMPLOI_ANORMAL": 0,
        "AMT_INCOME_TOTAL": revenu,
        "AMT_CREDIT": credit,
        "AMT_ANNUITY": round(credit / random.randint(24, 60)),
        "AMT_GOODS_PRICE": round(credit * 0.95),
        "NAME_CONTRACT_TYPE": "Cash loans",
        "EXT_SOURCE_1": ext[0], "EXT_SOURCE_2": ext[1], "EXT_SOURCE_3": ext[2],
    }


def generer():
    db = SessionLocal()
    service = ServiceModele()

    # Recuperer un utilisateur (le premier admin ou agent existant)
    utilisateur = db.query(models.User).first()
    if not utilisateur:
        print("Aucun utilisateur en base. Creez d'abord un compte via l'API.")
        return

    # Version du modele
    version = db.query(models.ModelVersion).filter(
        models.ModelVersion.en_production == True).first()
    if not version:
        version = models.ModelVersion(algorithme="Gradient Boosting", auc=0.753, en_production=True)
        db.add(version); db.commit(); db.refresh(version)

    # Creer les clients
    clients = []
    for nom in NOMS:
        c = models.Client(
            nom=nom, genre=random.choice(["M", "F"]),
            age=random.randint(23, 60),
            profession=random.choice(PROFESSIONS),
            situation_familiale=random.choice(SITUATIONS),
        )
        db.add(c); clients.append(c)
    db.commit()
    for c in clients:
        db.refresh(c)
    print(f"{len(clients)} clients crees.")

    # Creer des analyses reparties sur les 30 derniers jours
    nb_analyses = 60
    for i in range(nb_analyses):
        client = random.choice(clients)
        dossier = dossier_aleatoire()
        resultat = service.analyser(dossier)

        # Date repartie sur les 30 derniers jours
        jours = random.randint(0, 29)
        date = datetime.utcnow() - timedelta(days=jours, hours=random.randint(0, 23))

        # Resultat reel pour certaines analyses anciennes (pour le reentrainement)
        resultat_reel = None
        if jours > 15:  # les analyses assez anciennes ont un resultat connu
            # Le defaut reel correle a la proba (avec un peu de hasard)
            if random.random() < resultat["probabilite_defaut"]:
                resultat_reel = "defaut"
            else:
                resultat_reel = "rembourse"

        analyse = models.Analyse(
            probabilite_defaut=resultat["probabilite_defaut"],
            classe_risque=resultat["classe_risque"],
            decision=resultat["decision"],
            facteurs_explicatifs=json.dumps(resultat["facteurs_explicatifs"], ensure_ascii=False),
            explication=resultat.get("explication", ""),
            donnees_dossier=json.dumps(dossier, ensure_ascii=False),
            resultat_reel=resultat_reel,
            date_analyse=date,
            client_id=client.id, user_id=utilisateur.id,
            model_version_id=version.id,
        )
        db.add(analyse)
    db.commit()
    print(f"{nb_analyses} analyses creees, reparties sur 30 jours.")
    print("Donnees de test generees avec succes.")


if __name__ == "__main__":
    generer()
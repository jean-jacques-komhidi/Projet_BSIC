# -*- coding: utf-8 -*-
"""
Tests de la page Mon profil : regles de mot de passe, changement du mot de
passe (ancien exige, date enregistree), modification limitee au nom, et
statistiques (activite, issues a renseigner, modele en service).
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_base = os.path.join(tempfile.mkdtemp(), "test_profil.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_base}"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import Base, engine, SessionLocal
from app import models, auth_routes
from app.security import hacher_mot_de_passe, valider_mot_de_passe

app = FastAPI()
app.include_router(auth_routes.router)
client = TestClient(app)
MDP = "Ndjamena2026"


@pytest.fixture(autouse=True)
def base():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    agent = models.User(nom="Fatimé Abakar", email="fatime.abakar@bsic.td",
                        mot_de_passe=hacher_mot_de_passe(MDP), role="agent")
    db.add_all([agent, models.ModelVersion(algorithme="Gradient Boosting", auc=0.75, en_production=True,
                                           auc_reelle=0.624)])
    db.add(models.EtatSurveillance(cle="etat", valeur="ok"))
    db.commit()
    maintenant = datetime.utcnow()
    for jours, decision, issue in [(10, "ACCORDE", None), (60, "ACCORDE", None), (90, "ACCORDE", "rembourse"),
                                   (120, "REFUSE", None), (500, "ACCORDE", None)]:
        db.add(models.Analyse(user_id=agent.id, decision=decision, probabilite_defaut=0.3, resultat_reel=issue,
                              date_analyse=maintenant - timedelta(days=jours)))
    db.commit()
    db.close()


def _entetes(mdp=MDP):
    r = client.post("/auth/connexion", data={"username": "fatime.abakar@bsic.td", "password": mdp})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_regles_du_mot_de_passe():
    assert valider_mot_de_passe("Ndjamena2026", "Fatimé Abakar", "fatime.abakar@bsic.td") == []
    assert "au moins 8 caractères" in valider_mot_de_passe("Ab1", None, None)
    assert "une majuscule et une minuscule" in valider_mot_de_passe("ndjamena2026")
    assert "un chiffre" in valider_mot_de_passe("Ndjamena")
    assert "ne pas contenir votre nom ni votre e-mail" in valider_mot_de_passe("Abakar2026", "Fatimé Abakar")
    assert "ne pas contenir votre nom ni votre e-mail" in valider_mot_de_passe("Fatime.abakar1", None, "fatime.abakar@bsic.td")


def test_changement_du_mot_de_passe():
    e = _entetes()
    url = "/auth/moi/mot-de-passe"
    assert client.put(url, json={"ancien_mot_de_passe": "faux", "nouveau_mot_de_passe": "Tchad2026x"}, headers=e).status_code == 400
    faible = client.put(url, json={"ancien_mot_de_passe": MDP, "nouveau_mot_de_passe": "tchad"}, headers=e)
    assert faible.status_code == 400 and "8 caractères" in faible.json()["detail"]
    assert client.put(url, json={"ancien_mot_de_passe": MDP, "nouveau_mot_de_passe": MDP}, headers=e).status_code == 400
    assert client.put(url, json={"ancien_mot_de_passe": MDP, "nouveau_mot_de_passe": "Tchad2026x"}, headers=e).status_code == 200
    stats = client.get("/auth/moi/statistiques", headers=_entetes("Tchad2026x")).json()
    assert stats["jours_depuis_changement"] == 0 and stats["mot_de_passe_change_le"]


def test_seul_le_nom_est_modifiable_par_soi_meme():
    e = _entetes()
    assert client.put("/auth/moi", json={"email": "autre@bsic.td"}, headers=e).status_code == 403
    assert client.put("/auth/moi", json={"mot_de_passe": "Tchad2026x"}, headers=e).status_code == 400
    r = client.put("/auth/moi", json={"nom": "  Fatimé Abakar Mahamat "}, headers=e)
    assert r.status_code == 200 and r.json()["nom"] == "Fatimé Abakar Mahamat"
    # Le mot de passe n'a pas change
    _entetes()


def test_statistiques_du_profil():
    s = client.get("/auth/moi/statistiques", headers=_entetes()).json()
    assert s["analyses_realisees"] == 4            # 12 derniers mois
    assert s["credits_accordes"] == 3 and s["credits_refuses"] == 1
    assert s["taux_accord"] == 75
    assert s["issues_a_renseigner"] == 2           # accordes il y a 60 et 500 jours, sans issue
    assert s["mot_de_passe_change_le"] is None
    assert s["modele"] == {"version": 1, "algorithme": "Gradient Boosting", "mise_en_service": s["modele"]["mise_en_service"],
                           "auc_reelle": 0.624, "etat": "ok"}

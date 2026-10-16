# -*- coding: utf-8 -*-
"""
Tests de la liste des clients : synthese de leurs analyses et suppression
bloquee pour un client qui a des analyses.
"""

import os
import sys
import json
import tempfile
from datetime import datetime, timedelta
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_base = os.path.join(tempfile.mkdtemp(), "test_clients.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_base}"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import Base, engine, SessionLocal
from app import models, client_routes
from app.security import utilisateur_courant, administrateur_courant

app = FastAPI()
app.include_router(client_routes.router)
client = TestClient(app)
MAINTENANT = datetime.utcnow()


@pytest.fixture(autouse=True)
def base():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    admin = models.User(nom="Admin", email="a@x.td", mot_de_passe="x", role="admin")
    achta = models.Client(nom="Achta Oumar", genre="F", age=26)
    nouveau = models.Client(nom="Zara Oumar", genre="F", age=41)
    db.add_all([admin, achta, nouveau])
    db.commit()
    for jours, proba, decision, reel in [(90, 0.2, "ACCORDE", "rembourse"), (40, 0.4, "ACCORDE", None),
                                         (2, 0.8, "REFUSE", None)]:
        db.add(models.Analyse(client_id=achta.id, user_id=admin.id, decision=decision, probabilite_defaut=proba,
                              resultat_reel=reel, donnees_dossier=json.dumps({"AMT_CREDIT": 1_000_000}),
                              date_analyse=MAINTENANT - timedelta(days=jours)))
    db.commit()
    db.close()
    u = SimpleNamespace(id=1, role="admin", nom="Admin", email="a@x.td")
    app.dependency_overrides[utilisateur_courant] = lambda: u
    app.dependency_overrides[administrateur_courant] = lambda: u
    yield
    app.dependency_overrides.clear()


def test_synthese():
    liste = {c["nom"]: c for c in client.get("/clients/synthese").json()}
    achta, zara = liste["Achta Oumar"], liste["Zara Oumar"]
    assert achta["nb_analyses"] == 3
    assert achta["derniere_analyse"]["decision"] == "REFUSE"
    assert achta["tendance"] == 40
    assert achta["credits"] == {"accordes": 2, "rembourses": 1, "defauts": 0, "en_cours": 1,
                                "montant_accorde": 2_000_000}
    assert achta["a_surveiller"] and "Dernière demande refusée" in achta["motifs"]
    assert zara["nb_analyses"] == 0 and zara["derniere_analyse"] is None


def test_suppression_bloquee_si_analyses():
    r = client.delete("/clients/1")
    assert r.status_code == 409 and "3 analyses" in r.json()["detail"]
    assert client.delete("/clients/2").status_code == 200

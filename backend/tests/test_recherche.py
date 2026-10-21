# -*- coding: utf-8 -*-
"""Tests de la recherche globale (barre du haut) : clients, references et noms."""

import os
import sys
import json
import tempfile
from datetime import datetime, timedelta
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_base = os.path.join(tempfile.mkdtemp(), "test_recherche.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_base}"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import Base, engine, SessionLocal
from app import models, recherche_routes
from app.security import utilisateur_courant

app = FastAPI()
app.include_router(recherche_routes.router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def base():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    agent = models.User(nom="Agent", email="g@x.td", mot_de_passe="x", role="agent")
    achta, nour = models.Client(nom="Achta Oumar Abdoulaye"), models.Client(nom="Achta Nour")
    autre = models.Client(nom="Ali Mahamat Saleh")
    db.add_all([agent, achta, nour, autre])
    db.commit()
    maintenant = datetime.utcnow()
    for jours, p in [(30, 0.40), (20, 0.60), (2, 0.82)]:      # risque en hausse
        db.add(models.Analyse(client_id=achta.id, user_id=agent.id, probabilite_defaut=p, decision="REFUSE",
                              donnees_dossier=json.dumps({"AMT_CREDIT": 9_000_000}),
                              date_analyse=maintenant - timedelta(days=jours)))
    db.add(models.Analyse(client_id=nour.id, user_id=agent.id, probabilite_defaut=0.2, decision="ACCORDE",
                          date_analyse=maintenant - timedelta(days=5)))
    db.commit()
    u = SimpleNamespace(id=agent.id, role="agent", nom="Agent", email="g@x.td")
    db.close()
    app.dependency_overrides[utilisateur_courant] = lambda: u
    yield
    app.dependency_overrides.clear()


def test_recherche_par_nom():
    r = client.get("/recherche", params={"q": "achta"}).json()
    noms = [c["nom"] for c in r["clients"]]
    assert noms == ["Achta Nour", "Achta Oumar Abdoulaye"]
    oumar = r["clients"][1]
    assert oumar["nb_analyses"] == 3 and oumar["risque_en_hausse"] and oumar["derniere_analyse_id"]
    assert not r["clients"][0]["risque_en_hausse"]
    assert len(r["analyses"]) == 4 and r["analyses"][0]["client"] == "Achta Oumar Abdoulaye"
    assert r["analyses"][0]["montant"] == 9_000_000


def test_recherche_par_reference():
    for q in ("CRED-2026-0001", "cred20260001", "1"):
        r = client.get("/recherche", params={"q": q if q != "1" else "01"}).json()
        assert [a["id"] for a in r["analyses"]] == [1], q
    assert client.get("/recherche", params={"q": "CRED-2026-9999"}).json()["analyses"] == []


def test_texte_trop_court():
    assert client.get("/recherche", params={"q": "a"}).status_code == 422

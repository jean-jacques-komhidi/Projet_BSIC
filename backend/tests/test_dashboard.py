# -*- coding: utf-8 -*-
"""
Tests de la route du tableau de bord : periode, tranches de montant, issues
reelles, dossiers a suivre (par role) et heure du Tchad.
"""

import os
import sys
import json
import tempfile
from datetime import datetime, timedelta
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_base = os.path.join(tempfile.mkdtemp(), "test_dashboard.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_base}"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import Base, engine, SessionLocal
from app import models, dashboard_routes
from app.security import utilisateur_courant

app = FastAPI()
app.include_router(dashboard_routes.router)
client = TestClient(app)
MAINTENANT = datetime.utcnow()


@pytest.fixture(autouse=True)
def base():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    admin = models.User(nom="Admin", email="a@x.td", mot_de_passe="x", role="admin")
    agent = models.User(nom="Agent", email="g@x.td", mot_de_passe="x", role="agent")
    c = models.Client(nom="Ali Mahamat")
    db.add_all([admin, agent, c])
    db.commit()

    def ajout(jours, decision, montant, user, reel=None, proba=0.3, risque="faible"):
        db.add(models.Analyse(client_id=c.id, user_id=user.id, decision=decision, classe_risque=risque,
                              probabilite_defaut=proba, resultat_reel=reel,
                              donnees_dossier=json.dumps({"AMT_CREDIT": montant}),
                              date_analyse=MAINTENANT - timedelta(days=jours)))

    ajout(1, "ACCORDE", 500_000, agent)
    ajout(2, "ACCORDE", 2_000_000, agent, reel="rembourse")
    ajout(3, "REFUSE", 6_000_000, admin, proba=0.85, risque="eleve")
    ajout(45, "ACCORDE", 1_500_000, agent)          # a suivre (agent)
    ajout(60, "ACCORDE", 4_000_000, admin)          # a suivre (admin)
    ajout(90, "ACCORDE", 900_000, admin, reel="defaut")
    db.commit()
    ids = {"admin": admin.id, "agent": agent.id}
    db.close()
    yield ids
    app.dependency_overrides.clear()


def _en_tant_que(role, ids):
    app.dependency_overrides[utilisateur_courant] = lambda: SimpleNamespace(id=ids[role], role=role)


def test_periode_30_jours(base):
    _en_tant_que("admin", base)
    d = client.get("/dashboard?periode=30j").json()
    assert d["totaux"]["analyses"] == 3
    assert d["decisions"] == {"accordes": 2, "refuses": 1, "taux_acceptation": 66.7}
    assert d["issues_reelles"] == {"renseignees": 1, "credits_accordes": 2}
    assert len(d["evolution"]) == 30


def test_periode_tout_et_tranches(base):
    _en_tant_que("admin", base)
    d = client.get("/dashboard?periode=tout").json()
    assert d["totaux"]["analyses"] == 6
    tranches = {t["tranche"]: (t["accordes"], t["refuses"]) for t in d["decisions_par_montant"]}
    assert tranches == {"Moins de 1 M": (2, 0), "1 à 3 M": (2, 0), "3 à 5 M": (1, 0), "Plus de 5 M": (0, 1)}
    assert len(d["evolution"]) == 12


def test_dossiers_a_suivre_selon_le_role(base):
    _en_tant_que("admin", base)
    admin = client.get("/dashboard").json()["dossiers_a_suivre"]
    assert admin["total"] == 2
    assert admin["liste"][0]["jours"] >= 59          # le plus ancien en premier
    _en_tant_que("agent", base)
    agent = client.get("/dashboard").json()["dossiers_a_suivre"]
    assert agent["total"] == 1                        # uniquement ses propres dossiers


def test_periode_invalide_refusee(base):
    _en_tant_que("admin", base)
    assert client.get("/dashboard?periode=99j").status_code == 422


def test_heure_du_tchad():
    # 23h30 UTC le 14 = 00h30 le 15 a N'Djamena
    assert dashboard_routes._locale(datetime(2026, 10, 14, 23, 30)).day == 15

# -*- coding: utf-8 -*-
"""
Tests des droits administrateur : personne ne doit pouvoir devenir admin
sans etre designe par un admin existant.

Utilise une base SQLite temporaire (pas besoin de PostgreSQL en CI).
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_base = os.path.join(tempfile.mkdtemp(), "test_droits.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_base}"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import Base, engine, SessionLocal
from app import models, auth_routes
from app.security import hacher_mot_de_passe
from app.creer_admin import creer_premier_admin

app = FastAPI()
app.include_router(auth_routes.router)
client = TestClient(app)

MDP = "MotDePasse123"


@pytest.fixture(autouse=True)
def base_vide(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    for cle in ("ADMIN_EMAIL", "ADMIN_PASSWORD", "ADMIN_NOM"):
        monkeypatch.delenv(cle, raising=False)
    yield


def _ajouter(email, role):
    db = SessionLocal()
    db.add(models.User(nom=email, email=email,
                       mot_de_passe=hacher_mot_de_passe(MDP), role=role))
    db.commit()
    db.close()


def _jeton(email):
    r = client.post("/auth/connexion", data={"username": email, "password": MDP})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _nouvel_admin():
    return {"nom": "Pirate", "email": "pirate@exemple.com",
            "mot_de_passe": MDP, "role": "admin"}


def test_visiteur_ne_peut_pas_creer_de_compte():
    r = client.post("/auth/utilisateurs", json=_nouvel_admin())
    assert r.status_code == 401


def test_agent_ne_peut_pas_creer_d_admin():
    _ajouter("agent@exemple.com", "agent")
    r = client.post("/auth/utilisateurs", json=_nouvel_admin(),
                    headers=_jeton("agent@exemple.com"))
    assert r.status_code == 403


def test_agent_ne_peut_pas_se_promouvoir():
    _ajouter("agent@exemple.com", "agent")
    entetes = _jeton("agent@exemple.com")
    client.put("/auth/moi", json={"role": "admin"}, headers=entetes)
    r = client.get("/auth/moi", headers=entetes)
    assert r.json()["role"] == "agent"


def test_admin_peut_creer_un_compte():
    _ajouter("admin@exemple.com", "admin")
    r = client.post("/auth/utilisateurs", json=_nouvel_admin(),
                    headers=_jeton("admin@exemple.com"))
    assert r.status_code == 201


def test_dernier_admin_ne_peut_pas_etre_retrograde():
    _ajouter("admin@exemple.com", "admin")
    entetes = _jeton("admin@exemple.com")
    moi = client.get("/auth/moi", headers=entetes).json()
    r = client.put(f"/auth/utilisateurs/{moi['id']}", json={"role": "agent"},
                   headers=entetes)
    assert r.status_code == 400


def test_script_cree_le_premier_admin(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "chef@exemple.com")
    monkeypatch.setenv("ADMIN_PASSWORD", MDP)
    creer_premier_admin()
    r = client.get("/auth/moi", headers=_jeton("chef@exemple.com"))
    assert r.json()["role"] == "admin"


def test_script_ne_cree_pas_de_second_admin(monkeypatch):
    _ajouter("admin@exemple.com", "admin")
    monkeypatch.setenv("ADMIN_EMAIL", "intrus@exemple.com")
    monkeypatch.setenv("ADMIN_PASSWORD", MDP)
    creer_premier_admin()
    db = SessionLocal()
    assert db.query(models.User).filter(models.User.email == "intrus@exemple.com").first() is None
    db.close()

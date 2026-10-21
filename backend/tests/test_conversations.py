# -*- coding: utf-8 -*-
"""Tests des conversations : apercu dans la liste et dossier joint."""

import os
import sys
import tempfile
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_base = os.path.join(tempfile.mkdtemp(), "test_conversations.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_base}"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import Base, engine, SessionLocal
from app import models, conversation_routes
from app.security import utilisateur_courant

app = FastAPI()
app.include_router(conversation_routes.router)
client = TestClient(app)
IDS = {}


@pytest.fixture(autouse=True)
def base(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    agent = models.User(nom="Agent", email="g@x.td", mot_de_passe="x", role="agent")
    autre = models.User(nom="Autre", email="o@x.td", mot_de_passe="x", role="agent")
    achta = models.Client(nom="Achta Oumar Abdoulaye")
    db.add_all([agent, autre, achta])
    db.commit()
    a = models.Analyse(client_id=achta.id, user_id=agent.id, probabilite_defaut=0.82, decision="REFUSE",
                       date_analyse=datetime(2026, 10, 16))
    db.add(a)
    db.commit()
    IDS.update(agent=agent.id, autre=autre.id, analyse=a.id)
    db.close()
    u = SimpleNamespace(id=IDS["agent"], role="agent", nom="Agent", email="g@x.td")
    app.dependency_overrides[utilisateur_courant] = lambda: u
    monkeypatch.setattr(conversation_routes, "repondre",
                        lambda db, q, aid, **k: "## Bilan\n**Réponse** sur le dossier [PDF:12]")
    yield
    app.dependency_overrides.clear()


def _nouvelle():
    return client.post("/conversations").json()["id"]


def test_apercu_sans_markdown():
    cid = _nouvelle()
    assert client.get("/conversations").json()[0]["apercu"] is None
    client.post(f"/conversations/{cid}/message", json={"question": "Pourquoi ?"})
    apercu = client.get("/conversations").json()[0]["apercu"]
    assert apercu == "Bilan Réponse sur le dossier"


def test_dossier_joint_memorise_puis_retire():
    cid = _nouvelle()
    client.post(f"/conversations/{cid}/message", json={"question": "Pourquoi ?", "analyse_id": IDS["analyse"]})
    d = client.get(f"/conversations/{cid}").json()["dossier"]
    assert d == {"id": IDS["analyse"], "reference": f"CRED-2026-{IDS['analyse']:04d}",
                 "client": "Achta Oumar Abdoulaye"}
    # L'agent retire l'etiquette : le message suivant part sans dossier
    client.post(f"/conversations/{cid}/message", json={"question": "Et en general ?"})
    assert client.get(f"/conversations/{cid}").json()["dossier"] is None


def test_dossier_inexistant_refuse():
    cid = _nouvelle()
    r = client.post(f"/conversations/{cid}/message", json={"question": "?", "analyse_id": 999})
    assert r.status_code == 404
    assert client.get(f"/conversations/{cid}").json()["messages"] == []


def test_conversation_d_un_autre_agent_invisible():
    db = SessionLocal()
    conv = models.Conversation(titre="Privée", user_id=IDS["autre"], analyse_id=IDS["analyse"])
    db.add(conv)
    db.commit()
    cid = conv.id
    db.close()
    assert client.get(f"/conversations/{cid}").status_code == 404
    assert client.get("/conversations").json() == []

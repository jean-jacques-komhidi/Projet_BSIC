# -*- coding: utf-8 -*-
"""
Tests de l'historique et du detail d'une analyse : montant et agent dans la
liste, detail (dossier, endettement, historique du client, genre exclu des
facteurs) et issue reelle impossible sur un credit refuse.
"""

import os
import sys
import json
import tempfile
from datetime import datetime, timedelta
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_base = os.path.join(tempfile.mkdtemp(), "test_historique.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_base}"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import Base, engine, SessionLocal
from app import models, analyse_routes
from app.security import utilisateur_courant, administrateur_courant

app = FastAPI()
app.include_router(analyse_routes.router)
client = TestClient(app)
MAINTENANT = datetime.utcnow()
DOSSIER = {"AMT_CREDIT": 2_000_000, "AMT_ANNUITY": 100_000, "AMT_INCOME_TOTAL": 250_000,
           "AMT_GOODS_PRICE": 1_900_000, "AGE_ANNEES": 35, "NAME_CONTRACT_TYPE": "Cash loans",
           "OCCUPATION_TYPE": "Accountants", "CODE_GENDER": "F"}
FACTEURS = [{"variable": "CODE_GENDER_F", "contribution": 0.5},
            {"variable": "EXT_SOURCE_2", "contribution": -0.3},
            {"variable": "OCCUPATION_TYPE_Accountants", "contribution": 0.1}]


@pytest.fixture(autouse=True)
def base():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    admin = models.User(nom="Admin", email="a@x.td", mot_de_passe="x", role="admin")
    agent = models.User(nom="Fatimé Abakar", email="g@x.td", mot_de_passe="x", role="agent")
    c = models.Client(nom="Achta Oumar")
    db.add_all([admin, agent, c])
    db.commit()
    for jours, decision, proba in [(90, "ACCORDE", 0.2), (40, "ACCORDE", 0.5), (2, "REFUSE", 0.85)]:
        db.add(models.Analyse(client_id=c.id, user_id=agent.id, decision=decision, probabilite_defaut=proba,
                              classe_risque="eleve" if proba >= 0.7 else "faible",
                              facteurs_explicatifs=json.dumps(FACTEURS), donnees_dossier=json.dumps(DOSSIER),
                              date_analyse=MAINTENANT - timedelta(days=jours)))
    db.commit()
    ids = {"admin": admin.id}
    db.close()
    utilisateur = SimpleNamespace(id=ids["admin"], role="admin", nom="Admin", email="a@x.td")
    app.dependency_overrides[utilisateur_courant] = lambda: utilisateur
    app.dependency_overrides[administrateur_courant] = lambda: utilisateur
    yield
    app.dependency_overrides.clear()


def test_liste_avec_montant_et_agent():
    liste = client.get("/analyses").json()
    assert len(liste) == 3
    assert liste[0]["montant"] == 2_000_000
    assert liste[0]["nom_agent"] == "Fatimé Abakar"
    assert liste[0]["nom_client"] == "Achta Oumar"


def test_detail_dossier_et_historique():
    d = client.get("/analyses/3").json()
    detail = d["detail"]
    assert d["nom_agent"] == "Fatimé Abakar"
    assert detail["endettement"] == pytest.approx(0.4)
    assert dict(detail["credit"])["Montant demandé"] == "2 000 000 FCFA"
    # historique du client, du plus ancien au plus recent
    assert [a["id"] for a in detail["historique_client"]] == [1, 2, 3]
    # le genre n'est jamais presente comme facteur ; libelles traduits
    libelles = [f["libelle"] for f in detail["facteurs"]]
    assert "Genre" not in libelles and all("GENDER" not in f["variable"] for f in detail["facteurs"])
    assert {"libelle": "Profession", "valeur": "Comptable"}.items() <= next(
        f for f in detail["facteurs"] if f["libelle"] == "Profession").items()
    assert detail["conseils"]["titre"].startswith("Recommandations")


def test_issue_refusee_pour_un_credit_refuse():
    assert client.put("/analyses/3/resultat", params={"resultat": "defaut"}).status_code == 400
    r = client.put("/analyses/2/resultat", params={"resultat": "rembourse"})
    assert r.status_code == 200 and r.json()["resultat_reel"] == "rembourse"


def test_simulation_sans_enregistrement():
    avant = client.get("/analyses").json()
    r = client.post("/analyses/3/simulation", json={"montant": 1_000_000, "duree_mois": 24})
    assert r.status_code == 200
    sim = r.json()
    assert 0 <= sim["probabilite_defaut"] <= 1
    assert sim["decision"] in ("ACCORDE", "REFUSE")
    assert sim["echeance"] == round(1_000_000 / 24)
    assert sim["endettement"] == pytest.approx(1_000_000 / 24 / 250_000)
    assert isinstance(sim["pistes"], list)
    assert client.get("/analyses").json() == avant                 # rien n'est enregistre
    assert client.post("/analyses/3/simulation", json={"montant": 0, "duree_mois": 24}).status_code == 422


def test_changements_depuis_analyse_precedente():
    detail = client.get("/analyses/2").json()["detail"]
    assert detail["changements"]["id"] == 1
    assert detail["changements"]["lignes"] == []                    # meme dossier
    assert client.get("/analyses/1").json()["detail"]["changements"] is None


def test_suppression_reservee_a_l_admin():
    # Un agent ne peut pas supprimer (la vraie verification du role s'applique)
    del app.dependency_overrides[administrateur_courant]
    app.dependency_overrides[utilisateur_courant] = lambda: SimpleNamespace(id=2, role="agent")
    assert client.delete("/analyses/3").status_code == 403
    assert len(client.get("/analyses").json()) == 3


def test_suppression_par_l_admin():
    assert client.delete("/analyses/3").status_code == 204
    assert client.get("/analyses/3").status_code == 404
    assert len(client.get("/analyses").json()) == 2
    db = SessionLocal()
    assert db.query(models.Notification).filter(models.Notification.titre == "Analyse supprimée").count() == 1
    db.close()
    assert client.delete("/analyses/3").status_code == 404

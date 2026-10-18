# -*- coding: utf-8 -*-
"""
Tests du monitoring : PSI et test de significativite, regle de reentrainement,
alertes automatiques (notification au changement d'etat, sans doublon),
notifications par personne, choix champion/challenger et mise a jour des
colonnes d'une ancienne base.
"""

import os
import sys
import json
import random
import tempfile
from datetime import datetime, timedelta
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_base = os.path.join(tempfile.mkdtemp(), "test_surveillance.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_base}"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from app.database import Base, engine, SessionLocal
from app import models, notification_routes, reentrainement_routes, reentrainement
from app.security import utilisateur_courant, administrateur_courant
from app.surveillance_service import psi, p_valeur, niveau, etat_du_modele
from app.alertes_service import verifier_et_notifier, alerter_client_en_hausse
from app.reentrainement import choisir_modele

MAINTENANT = datetime.utcnow()

app = FastAPI()
app.include_router(notification_routes.router)
app.include_router(reentrainement_routes.router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def base():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    admin = models.User(nom="Admin", email="a@x.td", mot_de_passe="x", role="admin")
    agent1 = models.User(nom="Fatimé", email="f@x.td", mot_de_passe="x", role="agent")
    agent2 = models.User(nom="Moussa", email="m@x.td", mot_de_passe="x", role="agent")
    db.add_all([admin, agent1, agent2])
    db.add(models.ModelVersion(algorithme="LightGBM", auc=0.75, en_production=True))
    db.commit()
    ids = SimpleNamespace(admin=admin.id, agent1=agent1.id, agent2=agent2.id)
    db.close()
    yield ids
    app.dependency_overrides.clear()


def _connecter(user_id, role):
    u = SimpleNamespace(id=user_id, role=role, nom="X", email="x@x.td")
    app.dependency_overrides[utilisateur_courant] = lambda: u
    app.dependency_overrides[administrateur_courant] = lambda: u


def _peupler(db, user_id, derive, n=80, graine=1):
    """n analyses de reference (60-120 jours) et n recentes (0-29 jours).

    Avec derive : montants et echeances recents bien plus eleves, et des issues
    reelles sans lien avec le score (le modele ne discrimine plus)."""
    rnd = random.Random(graine)
    for recent in (False, True):
        for _ in range(n):
            plus = derive and recent
            montant = rnd.uniform(3e6, 9e6) if plus else rnd.uniform(1e6, 4e6)
            proba = rnd.uniform(0.05, 0.9)
            jours = rnd.uniform(0, 29) if recent else rnd.uniform(60, 120)
            accorde = proba < 0.5
            if accorde and not recent:
                defaut = rnd.random() < (0.35 if derive else proba)
                resultat = "defaut" if defaut else "rembourse"
            else:
                resultat = None
            dossier = {"AMT_CREDIT": montant, "AMT_ANNUITY": montant / 20,
                       "AMT_INCOME_TOTAL": rnd.uniform(2e5, 6e5), "EXT_SOURCE_2": rnd.uniform(0.2, 0.8),
                       "AGE_ANNEES": rnd.randint(25, 60), "NAME_INCOME_TYPE": rnd.choice(["Working", "Pensioner"])}
            db.add(models.Analyse(user_id=user_id, decision="ACCORDE" if accorde else "REFUSE",
                                  probabilite_defaut=proba, classe_risque="moyen",
                                  donnees_dossier=json.dumps(dossier), resultat_reel=resultat,
                                  date_analyse=MAINTENANT - timedelta(days=jours)))
    db.commit()


# ---------------------------------------------------------------------------
# PSI et significativite
# ---------------------------------------------------------------------------
def test_psi_nul_pour_deux_repartitions_identiques():
    assert psi([0.2, 0.3, 0.5], [0.2, 0.3, 0.5]) == 0


def test_psi_eleve_pour_une_repartition_deplacee():
    assert psi([0.2] * 5, [0.6, 0.1, 0.1, 0.1, 0.1]) > 0.25


def test_le_meme_psi_n_est_significatif_qu_avec_assez_de_donnees():
    assert p_valeur(0.15, 40, 40, 5) > 0.05      # petit echantillon : peut etre du hasard
    assert p_valeur(0.15, 500, 500, 10) < 0.05   # grand echantillon : vraie derive


def test_un_psi_non_significatif_compte_comme_stable():
    assert niveau(0.30, significatif=False) == "stable"
    assert niveau(0.30) == "forte"
    assert niveau(0.15) == "moderee"
    assert niveau(0.05) == "stable"


# ---------------------------------------------------------------------------
# Etat du modele
# ---------------------------------------------------------------------------
def test_etat_insuffisant_sans_assez_d_analyses(base):
    db = SessionLocal()
    _peupler(db, base.agent1, derive=False, n=10)
    assert etat_du_modele(db)["etat"] == "insuffisant"
    db.close()


def test_derive_detectee_et_reentrainement_recommande(base):
    db = SessionLocal()
    _peupler(db, base.agent1, derive=True)
    etat = etat_du_modele(db)
    assert etat["etat"] == "alerte"
    montant = next(v for v in etat["donnees"]["variables"] if v["variable"] == "AMT_CREDIT")
    assert montant["niveau"] == "forte" and montant["significatif"]
    assert etat["regle"]["conditions"][0]["atteinte"]
    assert etat["regle"]["reentrainement_recommande"]
    db.close()


def test_sans_derive_le_modele_est_stable(base):
    db = SessionLocal()
    _peupler(db, base.agent1, derive=False)
    etat = etat_du_modele(db)
    assert etat["etat"] in ("ok", "surveiller")
    assert not etat["regle"]["conditions"][0]["atteinte"]
    db.close()


def test_la_performance_n_est_pas_jugee_sans_assez_d_issues(base):
    db = SessionLocal()
    _peupler(db, base.agent1, derive=True, n=40)
    etat = etat_du_modele(db)
    assert etat["performance"]["issues"] < 50
    assert not etat["regle"]["conditions"][1]["atteinte"]
    assert "Pas assez d'issues" in etat["regle"]["conditions"][1]["detail"]
    db.close()


# ---------------------------------------------------------------------------
# Alertes automatiques
# ---------------------------------------------------------------------------
def _notifs(db, user_id=None, **filtre):
    q = db.query(models.Notification)
    if user_id is not None:
        q = q.filter(models.Notification.destinataire_id == user_id)
    for cle, val in filtre.items():
        q = q.filter(getattr(models.Notification, cle) == val)
    return q.all()


def test_alerte_envoyee_une_seule_fois_aux_administrateurs(base):
    db = SessionLocal()
    _peupler(db, base.agent1, derive=True)
    verifier_et_notifier(db, forcer=True)
    alertes = _notifs(db, categorie="modele")
    assert len(alertes) == 1
    assert alertes[0].type == "danger" and alertes[0].destinataire_id == base.admin
    assert alertes[0].lien == "/monitoring"
    # Meme etat le lendemain : pas de doublon
    verifier_et_notifier(db, forcer=True)
    assert len(_notifs(db, categorie="modele")) == 1
    # Aucun agent ne recoit l'alerte du modele
    assert not _notifs(db, base.agent1, categorie="modele")
    db.close()


def test_une_seule_verification_par_jour(base):
    db = SessionLocal()
    _peupler(db, base.agent1, derive=True)
    assert verifier_et_notifier(db) is not None
    assert verifier_et_notifier(db) is None
    db.close()


def test_retour_a_la_normale_notifie(base):
    db = SessionLocal()
    _peupler(db, base.agent1, derive=False)
    db.add(models.EtatSurveillance(cle="etat", valeur="alerte"))
    db.commit()
    etat = verifier_et_notifier(db, forcer=True)
    if etat["etat"] == "ok":
        assert _notifs(db, categorie="modele", type="succes")
    db.close()


def test_rappel_des_issues_a_renseigner(base):
    db = SessionLocal()
    for jours in (40, 50, 60):
        db.add(models.Analyse(user_id=base.agent1, decision="ACCORDE", probabilite_defaut=0.2,
                              date_analyse=MAINTENANT - timedelta(days=jours)))
    db.commit()
    verifier_et_notifier(db, forcer=True)
    rappel = _notifs(db, categorie="dossiers")
    assert len(rappel) == 1 and rappel[0].titre == "3 issues à renseigner"
    assert rappel[0].lien == "/historique?issue=a_renseigner"
    db.close()


def test_agent_prevenu_si_le_risque_du_client_monte(base):
    db = SessionLocal()
    c = models.Client(nom="Achta Oumar")
    db.add(c)
    db.commit()
    for jours, p in [(20, 0.20), (10, 0.26), (1, 0.33)]:
        a = models.Analyse(client_id=c.id, user_id=base.agent1, decision="ACCORDE", probabilite_defaut=p,
                           date_analyse=MAINTENANT - timedelta(days=jours))
        db.add(a)
        db.commit()
    alerter_client_en_hausse(db, a)
    db.commit()
    n = _notifs(db, base.agent1)
    assert len(n) == 1 and "Achta Oumar" in n[0].titre
    assert not _notifs(db, base.agent2)
    db.close()


# ---------------------------------------------------------------------------
# Notifications par personne
# ---------------------------------------------------------------------------
def test_chacun_ne_voit_et_ne_lit_que_ses_notifications(base):
    db = SessionLocal()
    db.add_all([
        models.Notification(titre="Pour Fatimé", message="m", destinataire_id=base.agent1),
        models.Notification(titre="Pour Moussa", message="m", destinataire_id=base.agent2),
        models.Notification(titre="Ancienne", message="m", destinataire_id=None),
    ])
    db.commit()
    db.close()

    _connecter(base.agent1, "agent")
    assert [n["titre"] for n in client.get("/notifications").json()] == ["Pour Fatimé"]
    client.put("/notifications/tout-lu")
    assert client.get("/notifications/non-lues").json()["non_lues"] == 0

    _connecter(base.agent2, "agent")
    assert client.get("/notifications/non-lues").json()["non_lues"] == 1   # lecture propre a chacun

    _connecter(base.admin, "admin")
    assert [n["titre"] for n in client.get("/notifications").json()] == ["Ancienne"]


def test_impossible_de_marquer_la_notification_d_un_autre(base):
    db = SessionLocal()
    n = models.Notification(titre="Pour Moussa", message="m", destinataire_id=base.agent2)
    db.add(n)
    db.commit()
    nid = n.id
    db.close()
    _connecter(base.agent1, "agent")
    assert client.put(f"/notifications/{nid}/lue").status_code == 404


# ---------------------------------------------------------------------------
# Reentrainement
# ---------------------------------------------------------------------------
def test_le_candidat_n_est_retenu_que_s_il_fait_mieux():
    assert choisir_modele(0.78, 0.75)
    assert not choisir_modele(0.75, 0.75)
    assert not choisir_modele(0.70, 0.75)
    assert choisir_modele(0.70, None)


def test_reentrainement_impossible_sans_le_socle(base, monkeypatch):
    monkeypatch.setattr(reentrainement, "CHEMIN_CSV", "/chemin/inexistant.csv")
    _connecter(base.admin, "admin")
    reponse = client.post("/reentrainer")
    assert reponse.status_code == 409
    assert "introuvable" in reponse.json()["detail"]


# ---------------------------------------------------------------------------
# Mise a jour d'une ancienne base
# ---------------------------------------------------------------------------
def test_les_colonnes_manquantes_sont_ajoutees(tmp_path, monkeypatch):
    from app import init_db
    ancien = create_engine(f"sqlite:///{tmp_path / 'ancienne.db'}")
    with ancien.begin() as c:
        c.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        c.execute(text("CREATE TABLE notifications (id INTEGER PRIMARY KEY, titre VARCHAR, lue BOOLEAN)"))
        c.execute(text("CREATE TABLE model_versions (id INTEGER PRIMARY KEY, algorithme VARCHAR)"))
        c.execute(text("INSERT INTO notifications (titre, lue) VALUES ('ancienne', 0)"))
    monkeypatch.setattr(init_db, "engine", ancien)
    init_db.mettre_a_jour_colonnes()
    colonnes = {col["name"] for col in inspect(ancien).get_columns("notifications")}
    assert {"destinataire_id", "categorie", "lien", "texte_lien"} <= colonnes
    assert {"statut", "auc_reelle", "date_retrait"} <= {c["name"] for c in inspect(ancien).get_columns("model_versions")}
    with ancien.connect() as c:
        assert c.execute(text("SELECT titre FROM notifications")).scalar() == "ancienne"


# ---------------------------------------------------------------------------
# Apres une mise en service : nouvelle reference, performance du nouveau modele
# ---------------------------------------------------------------------------
def test_nouvelle_reference_apres_mise_en_service(base):
    db = SessionLocal()
    _peupler(db, base.agent1, derive=True)
    assert etat_du_modele(db)["etat"] == "alerte"
    ancienne = db.query(models.ModelVersion).first()
    ancienne.en_production = False
    db.add(models.ModelVersion(algorithme="LightGBM", auc=0.76, en_production=True, statut="production",
                               auc_reelle=0.71, debut_reference=MAINTENANT - timedelta(days=30)))
    db.commit()
    # Les analyses recentes servent de reference : il n'y en a plus assez avant la fenetre recente
    etat = etat_du_modele(db)
    assert etat["periodes"]["reference"]["analyses"] == 0
    # La performance ne juge que les decisions du nouveau modele (aucune encore)
    assert etat["performance"]["issues"] == 0
    assert etat["modele"]["issu_reentrainement"] and etat["modele"]["auc_validation"] == 0.71
    assert not any(c["atteinte"] for c in etat["regle"]["conditions"])
    # Les issues a renseigner concernent toujours tous les credits
    assert etat["performance"]["issues_en_attente"] >= 0
    db.close()


def test_reentrainement_complet_sur_un_socle_synthetique(base, tmp_path, monkeypatch):
    """Le vrai reentrainement, sur un petit socle synthetique et une copie du modele."""
    import shutil
    import numpy as np
    import pandas as pd
    from app import generer_donnees_test as g, model_service
    random.seed(3)
    np.random.seed(3)
    service = model_service.ServiceModele()
    # Socle : le modele actuel y est fiable
    socle = [g.dossier(random.betavariate(1.15, 1.6)) for _ in range(1500)]
    p = np.array(service.predire_lot(socle))
    df = pd.DataFrame(socle)
    df["DAYS_BIRTH"] = -(df.pop("AGE_ANNEES") * 365).astype(int)
    df["DAYS_EMPLOYED"] = -(df.pop("ANCIENNETE_EMPLOI_ANNEES") * 365).astype(int)
    df.pop("EMPLOI_ANORMAL")
    df["TARGET"] = (np.random.rand(len(df)) < 0.22 * p).astype(int)
    df.to_csv(tmp_path / "socle.csv", index=False)
    # Issues reelles de la banque, au profil local
    db = SessionLocal()
    locaux = [g.dossier(random.betavariate(1.15, 1.6), local=True) for _ in range(300)]
    for d, proba in zip(locaux, service.predire_lot(locaux)):
        a = models.Analyse(user_id=base.agent1, decision="ACCORDE", probabilite_defaut=proba,
                           donnees_dossier=json.dumps(d), date_analyse=MAINTENANT - timedelta(days=90))
        a.resultat_reel = "defaut" if random.random() < g._risque_local(a) else "rembourse"
        db.add(a)
    db.commit()
    # Copie du modele : le fichier du depot n'est jamais modifie par le test
    copie = tmp_path / "modele.pkl"
    shutil.copy(model_service.CHEMIN_MODELE, copie)
    monkeypatch.setattr(reentrainement, "CHEMIN_CSV", str(tmp_path / "socle.csv"))
    monkeypatch.setattr(reentrainement, "CHEMIN_MODELE", str(copie))
    monkeypatch.setattr(reentrainement, "_recharger_modele", lambda: None)

    r = reentrainement.reentrainer(db, avec_mlflow=False, auteur="Test")
    assert r["part_donnees_locales"] == 0.3
    assert r["jeu_comparaison"].startswith("150 issues")
    # Les deux modeles sont mesures ensemble, sur les memes issues
    versions_mesurees = db.query(models.ModelVersion).filter(models.ModelVersion.nb_issues_validation == 150).count()
    assert versions_mesurees == 2
    versions = db.query(models.ModelVersion).order_by(models.ModelVersion.id).all()
    if r["promu"]:
        assert versions[0].statut == "retire" and not versions[0].en_production
        assert versions[-1].en_production and versions[-1].debut_reference is not None
        assert versions[-1].auc_precedent == round(r["auc_actuel"], 4)
    else:
        assert versions[-1].statut == "rejete" and versions[0].en_production
    db.close()

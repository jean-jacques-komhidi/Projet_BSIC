# -*- coding: utf-8 -*-
"""
Reentrainement du modele CREDISCORE.

Ce module reentraine les modeles en combinant deux sources de donnees :
- le socle historique (application_train.csv),
- les analyses reelles resolues de la base (celles dont le resultat_reel est
  connu : 'rembourse' ou 'defaut').

Les issues reelles, peu nombreuses, recoivent 30 % du poids total de
l'apprentissage (donnees locales et recentes). Les trois modeles sont
reentraines ; le meilleur devient le candidat. Il est
compare au modele en service sur les memes donnees et ne le remplace que s'il
fait mieux (principe champion / challenger). La decision est enregistree dans
les versions du modele.

Ce module est appele par la route /reentrainer.
"""

import os
import json
from datetime import datetime, timedelta
import joblib
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score

from sqlalchemy.orm import Session
from . import models

GRAINE = 42

# Poids des issues reelles de la banque dans l'apprentissage. Elles sont peu
# nombreuses face au socle (environ 300 000 dossiers etrangers) : sans
# ponderation, elles ne pesent rien. Comme en banque, on donne plus de poids aux
# donnees locales et recentes : ici 30 % du poids total, quel que soit leur nombre.
PART_DONNEES_LOCALES = 0.30

# Chemins : le CSV socle et le modele de sortie
CHEMIN_CSV = os.path.join(os.path.dirname(__file__), "..", "notebook", "application_train.csv")
CHEMIN_MODELE = os.path.join(os.path.dirname(__file__), "..", "models", "modele_credistore.pkl")

COLONNES = [
    "CNT_CHILDREN", "CNT_FAM_MEMBERS", "AMT_INCOME_TOTAL", "AMT_CREDIT",
    "AMT_ANNUITY", "AMT_GOODS_PRICE", "EXT_SOURCE_1", "EXT_SOURCE_2",
    "EXT_SOURCE_3", "EMPLOI_ANORMAL", "AGE_ANNEES", "ANCIENNETE_EMPLOI_ANNEES",
    "CODE_GENDER", "NAME_FAMILY_STATUS", "NAME_EDUCATION_TYPE",
    "OCCUPATION_TYPE", "ORGANIZATION_TYPE", "NAME_INCOME_TYPE",
    "NAME_CONTRACT_TYPE",
]


def _charger_socle():
    """Charge et prepare le socle historique (CSV), renvoie X et y."""
    df_full = pd.read_csv(CHEMIN_CSV)
    variables = [
        "DAYS_BIRTH", "CODE_GENDER", "NAME_FAMILY_STATUS", "CNT_CHILDREN",
        "CNT_FAM_MEMBERS", "NAME_EDUCATION_TYPE", "OCCUPATION_TYPE",
        "ORGANIZATION_TYPE", "NAME_INCOME_TYPE", "DAYS_EMPLOYED",
        "AMT_INCOME_TOTAL", "AMT_CREDIT", "AMT_ANNUITY", "AMT_GOODS_PRICE",
        "NAME_CONTRACT_TYPE", "EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3",
        "TARGET",
    ]
    df = df_full[variables].copy()
    df["EMPLOI_ANORMAL"] = (df["DAYS_EMPLOYED"] == 365243).astype(int)
    df["DAYS_EMPLOYED"] = df["DAYS_EMPLOYED"].replace(365243, np.nan)
    df["AGE_ANNEES"] = (-df["DAYS_BIRTH"] / 365).round(1)
    df["ANCIENNETE_EMPLOI_ANNEES"] = (-df["DAYS_EMPLOYED"] / 365).round(1)
    df = df.drop(columns=["DAYS_BIRTH", "DAYS_EMPLOYED"])
    df["CODE_GENDER"] = df["CODE_GENDER"].replace("XNA", "F")
    plafond = df["AMT_INCOME_TOTAL"].quantile(0.999)
    df["AMT_INCOME_TOTAL"] = df["AMT_INCOME_TOTAL"].clip(upper=plafond)
    y = df["TARGET"]
    X = df.drop(columns=["TARGET"])
    return X, y


def _charger_analyses_resolues(db: Session):
    """Charge les analyses de la base dont le resultat reel est connu.

    Renvoie un DataFrame X et une serie y (0 = rembourse, 1 = defaut), ou
    (None, None) s'il n'y en a aucune.
    """
    analyses = db.query(models.Analyse).filter(
        models.Analyse.resultat_reel.in_(["rembourse", "defaut"])
    ).all()
    if not analyses:
        return None, None

    lignes, cibles = [], []
    for a in analyses:
        if not a.donnees_dossier:
            continue
        dossier = json.loads(a.donnees_dossier)
        ligne = {c: dossier.get(c) for c in COLONNES}
        lignes.append(ligne)
        cibles.append(1 if a.resultat_reel == "defaut" else 0)

    if not lignes:
        return None, None
    return pd.DataFrame(lignes), pd.Series(cibles)


def _decouper_issues(X_reel, y_reel):
    """Moitie des issues reelles pour l'entrainement, moitie pour juger les modeles.

    Si elles sont trop peu nombreuses (ou d'une seule classe), elles servent
    toutes a l'entrainement et les modeles sont juges sur le socle."""
    if X_reel is None or len(X_reel) < 40 or y_reel.nunique() < 2 or y_reel.value_counts().min() < 4:
        return X_reel, y_reel, None, None
    X_a, X_e, y_a, y_e = train_test_split(X_reel, y_reel, test_size=0.5, random_state=GRAINE, stratify=y_reel)
    return X_a, y_a, X_e, y_e


def choisir_modele(auc_candidat: float, auc_actuel) -> bool:
    """Le candidat ne remplace le modele en service que s'il fait mieux."""
    return auc_actuel is None or auc_candidat > auc_actuel


def _recharger_modele():
    """Le nouveau modele est utilise tout de suite, sans redemarrer le serveur."""
    from .model_service import ServiceModele
    from . import analyse_routes
    nouveau = ServiceModele()
    analyse_routes.service = nouveau
    try:
        from . import main
        main.service = nouveau
    except Exception:
        pass


def reentrainer(db: Session, avec_mlflow=True, auteur: str = None):
    """Reentraine un modele candidat et ne le met en service que s'il bat le modele actuel.

    1. Entrainement des trois algorithmes sur le socle et une partie des issues reelles ;
       le meilleur devient le candidat.
    2. Le candidat et le modele en service sont evalues sur les MEMES donnees : les
       issues reelles mises de cote (ou, a defaut, le jeu de test du socle).
    3. Mise en service seulement si le candidat fait mieux ; sinon le modele actuel est
       conserve et le candidat est enregistre comme rejete.
    """
    if not os.path.exists(CHEMIN_CSV):
        raise FileNotFoundError(
            "Le socle d'entraînement (notebook/application_train.csv) est introuvable sur ce serveur : "
            "lancez le réentraînement depuis la machine qui le possède.")

    # 1. Donnees
    X, y = _charger_socle()
    nb_socle = len(X)
    X_reel, y_reel = _charger_analyses_resolues(db)
    nb_reel = 0 if X_reel is None else len(X_reel)
    X_reel_app, y_reel_app, X_eval, y_eval = _decouper_issues(X_reel, y_reel)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=GRAINE, stratify=y)
    poids = np.ones(len(X_train))
    nb_reel_app = 0 if X_reel_app is None else len(X_reel_app)
    if nb_reel_app:
        poids_local = PART_DONNEES_LOCALES / (1 - PART_DONNEES_LOCALES) * len(X_train) / nb_reel_app
        poids = np.concatenate([poids, np.full(nb_reel_app, poids_local)])
        X_train = pd.concat([X_train, X_reel_app], ignore_index=True)
        y_train = pd.concat([y_train, y_reel_app], ignore_index=True)

    colonnes_num = X_train.select_dtypes(include=[np.number]).columns.tolist()
    colonnes_cat = [c for c in X_train.columns if c not in colonnes_num]
    preparateur = ColumnTransformer([
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median")),
                          ("scaler", StandardScaler())]), colonnes_num),
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                          ("encoder", OneHotEncoder(handle_unknown="ignore",
                                                    sparse_output=False))]), colonnes_cat),
    ])

    modeles = {
        "Regression logistique": LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=GRAINE),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, max_depth=10, min_samples_leaf=50,
            class_weight="balanced", n_jobs=-1, random_state=GRAINE),
        "Gradient Boosting": LGBMClassifier(
            n_estimators=200, learning_rate=0.05, num_leaves=20,
            class_weight="balanced", n_jobs=-1, random_state=GRAINE, verbose=-1),
    }

    if avec_mlflow:
        try:
            import mlflow, mlflow.sklearn
            mlflow.set_tracking_uri("http://127.0.0.1:5000")
            mlflow.set_experiment("CREDISCORE_BSIC")
        except Exception:
            avec_mlflow = False

    # 2. Entrainement et choix du candidat (sur le jeu de test du socle)
    resultats = {}
    for nom, clf in modeles.items():
        pipe = Pipeline([("prep", preparateur), ("clf", clf)])
        pipe.fit(X_train, y_train, clf__sample_weight=poids)
        auc_test = roc_auc_score(y_test, pipe.predict_proba(X_test)[:, 1])
        resultats[nom] = {"pipeline": pipe, "auc_test": auc_test}
        if avec_mlflow:
            try:
                with mlflow.start_run(run_name=f"reentrainement_{nom}"):
                    mlflow.log_param("algorithme", nom)
                    mlflow.log_param("nb_donnees_socle", nb_socle)
                    mlflow.log_param("nb_donnees_reelles", nb_reel)
                    mlflow.log_param("part_donnees_locales", PART_DONNEES_LOCALES if nb_reel_app else 0)
                    mlflow.log_metric("auc_test", auc_test)
            except Exception:
                avec_mlflow = False

    nom_candidat = max(resultats, key=lambda n: resultats[n]["auc_test"])
    candidat = resultats[nom_candidat]["pipeline"]
    auc_socle = resultats[nom_candidat]["auc_test"]

    # 3. Comparaison avec le modele en service, sur les memes donnees
    if X_eval is not None:
        X_cmp, y_cmp, jeu = X_eval, y_eval, f"{len(X_eval)} issues réelles mises de côté"
    else:
        X_cmp, y_cmp, jeu = X_test, y_test, "jeu de test du socle (pas assez d'issues réelles)"
    auc_candidat = roc_auc_score(y_cmp, candidat.predict_proba(X_cmp)[:, 1])
    try:
        actuel = joblib.load(CHEMIN_MODELE)
        auc_actuel = roc_auc_score(y_cmp, actuel.predict_proba(X_cmp)[:, 1])
    except Exception:
        auc_actuel = None
    promu = choisir_modele(auc_candidat, auc_actuel)

    # 4. Enregistrement de la decision
    maintenant = datetime.utcnow()
    en_service = db.query(models.ModelVersion).filter(models.ModelVersion.en_production == True).first()  # noqa: E712
    reelle = X_eval is not None
    if promu:
        joblib.dump(candidat, CHEMIN_MODELE)
        if en_service:
            en_service.en_production = False
            en_service.statut = "retire"
            en_service.date_retrait = maintenant
            if reelle and auc_actuel is not None:
                en_service.auc_reelle = round(auc_actuel, 4)
        # Nouvelle reference de surveillance : les mois recents que le nouveau modele a appris
        from .surveillance_service import JOURS_REFERENCE_NOUVEAU_MODELE
        db.add(models.ModelVersion(algorithme=nom_candidat, auc=round(auc_socle, 4), en_production=True,
                                   statut="production", auc_reelle=round(auc_candidat, 4) if reelle else None,
                                   debut_reference=maintenant - timedelta(days=JOURS_REFERENCE_NOUVEAU_MODELE)))
    else:
        db.add(models.ModelVersion(algorithme=nom_candidat, auc=round(auc_socle, 4), en_production=False,
                                   statut="rejete", auc_reelle=round(auc_candidat, 4) if reelle else None))
        if en_service and reelle and auc_actuel is not None:
            en_service.auc_reelle = round(auc_actuel, 4)
    db.commit()
    if promu:
        _recharger_modele()
        # Verification immediate : l'administrateur voit tout de suite le nouvel etat
        try:
            from .alertes_service import verifier_et_notifier
            verifier_et_notifier(db, forcer=True)
        except Exception:
            pass

    return {
        "promu": promu,
        "meilleur_modele": nom_candidat,
        "auc_test": round(auc_socle, 4),
        "auc_candidat": round(auc_candidat, 4),
        "auc_actuel": round(auc_actuel, 4) if auc_actuel is not None else None,
        "jeu_comparaison": jeu,
        "donnees_socle": nb_socle,
        "donnees_reelles_integrees": nb_reel,
        "part_donnees_locales": PART_DONNEES_LOCALES if nb_reel_app else 0,
        "total_donnees": nb_socle + nb_reel,
        "auteur": auteur,
    }

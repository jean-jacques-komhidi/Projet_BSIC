# -*- coding: utf-8 -*-
"""
Reentrainement du modele CREDISCORE.

Ce module reentraine les modeles en combinant deux sources de donnees :
- le socle historique (application_train.csv),
- les analyses reelles resolues de la base (celles dont le resultat_reel est
  connu : 'rembourse' ou 'defaut').

Les trois modeles sont reentraines et compares ; le meilleur est sauvegarde
et enregistre dans MLflow. Une nouvelle version est creee en base et marquee
en production.

Ce module est appele par la route /reentrainer.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
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


def reentrainer(db: Session, avec_mlflow=True):
    """Reentraine les modeles sur le socle + les analyses resolues.

    Renvoie un dictionnaire resumant le resultat (meilleur modele, AUC,
    nombre d'analyses reelles integrees).
    """
    # 1. Charger le socle
    X, y = _charger_socle()
    nb_socle = len(X)

    # 2. Ajouter les analyses resolues de la base, si presentes
    X_reel, y_reel = _charger_analyses_resolues(db)
    nb_reel = 0
    if X_reel is not None:
        nb_reel = len(X_reel)
        X = pd.concat([X, X_reel], ignore_index=True)
        y = pd.concat([y, y_reel], ignore_index=True)

    # 3. Separation train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=GRAINE, stratify=y)

    colonnes_num = X_train.select_dtypes(include=[np.number]).columns.tolist()
    colonnes_cat = [c for c in X_train.columns if c not in colonnes_num]
    preparateur = ColumnTransformer([
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median")),
                          ("scaler", StandardScaler())]), colonnes_num),
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                          ("encoder", OneHotEncoder(handle_unknown="ignore",
                                                    sparse_output=False))]), colonnes_cat),
    ])

    # 4. Definir et entrainer les trois modeles
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

    # MLflow (optionnel)
    if avec_mlflow:
        try:
            import mlflow, mlflow.sklearn
            mlflow.set_tracking_uri("http://127.0.0.1:5000")
            mlflow.set_experiment("CREDISCORE_BSIC")
        except Exception:
            avec_mlflow = False

    resultats = {}
    for nom, clf in modeles.items():
        pipe = Pipeline([("prep", preparateur), ("clf", clf)])
        pipe.fit(X_train, y_train)
        proba = pipe.predict_proba(X_test)[:, 1]
        auc_test = roc_auc_score(y_test, proba)
        resultats[nom] = {"pipeline": pipe, "auc_test": auc_test}

        if avec_mlflow:
            with mlflow.start_run(run_name=f"reentrainement_{nom}"):
                mlflow.log_param("algorithme", nom)
                mlflow.log_param("nb_donnees_socle", nb_socle)
                mlflow.log_param("nb_donnees_reelles", nb_reel)
                mlflow.log_metric("auc_test", auc_test)
                mlflow.sklearn.log_model(pipe, name="modele",
                                         serialization_format="cloudpickle")

    # 5. Selection du meilleur et sauvegarde
    meilleur_nom = max(resultats, key=lambda n: resultats[n]["auc_test"])
    meilleur = resultats[meilleur_nom]["pipeline"]
    auc = resultats[meilleur_nom]["auc_test"]
    joblib.dump(meilleur, CHEMIN_MODELE)

    # 6. Enregistrer la nouvelle version en base et la marquer en production
    #    (les anciennes versions sont retirees de la production)
    db.query(models.ModelVersion).update({models.ModelVersion.en_production: False})
    nouvelle = models.ModelVersion(
        algorithme=meilleur_nom, auc=round(auc, 4), en_production=True)
    db.add(nouvelle)
    db.commit()

    return {
        "meilleur_modele": meilleur_nom,
        "auc_test": round(auc, 4),
        "donnees_socle": nb_socle,
        "donnees_reelles_integrees": nb_reel,
        "total_donnees": nb_socle + nb_reel,
    }
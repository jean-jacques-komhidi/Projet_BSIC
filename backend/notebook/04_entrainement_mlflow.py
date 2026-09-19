# -*- coding: utf-8 -*-
"""
CREDISCORE-BSIC - Entrainement avec suivi MLflow

Ce script reprend le pipeline d'entrainement (chargement, preparation,
entrainement et comparaison des trois modeles) et l'integre a MLflow pour
le suivi et le versioning des modeles.

A chaque modele entraine, MLflow enregistre :
- les parametres (algorithme, reglages),
- les metriques (AUC en validation croisee, AUC sur le test, cout metier),
- le modele lui-meme (le pipeline complet).

Le meilleur modele est ensuite marque et sauvegarde en .pkl pour l'API.

Prerequis :
- Le serveur MLflow doit tourner (mlflow server ... --port 5000)
- Le fichier application_train.csv doit etre accessible

Utilisation :
    python 04_entrainement_mlflow.py
"""

import pandas as pd
import numpy as np
import warnings
import joblib
warnings.filterwarnings("ignore")

from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score, confusion_matrix

import mlflow
import mlflow.sklearn

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GRAINE = 42
np.random.seed(GRAINE)
COUT_FN = 5   # cout d'un faux negatif
COUT_FP = 1   # cout d'un faux positif

# Adresse du serveur MLflow (celui que vous avez lance sur le port 5000)
mlflow.set_tracking_uri("http://127.0.0.1:5000")
# Nom de l'experience : tous les entrainements y seront regroupes
mlflow.set_experiment("CREDISCORE_BSIC")

CHEMIN_DONNEES = "application_train.csv"


# ---------------------------------------------------------------------------
# 1. Chargement et preparation des donnees (identique au notebook)
# ---------------------------------------------------------------------------
def preparer_donnees():
    df_full = pd.read_csv(CHEMIN_DONNEES)
    variables_bsic = [
        "DAYS_BIRTH", "CODE_GENDER", "NAME_FAMILY_STATUS", "CNT_CHILDREN",
        "CNT_FAM_MEMBERS", "NAME_EDUCATION_TYPE", "OCCUPATION_TYPE",
        "ORGANIZATION_TYPE", "NAME_INCOME_TYPE", "DAYS_EMPLOYED",
        "AMT_INCOME_TOTAL", "AMT_CREDIT", "AMT_ANNUITY", "AMT_GOODS_PRICE",
        "NAME_CONTRACT_TYPE", "EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3",
        "TARGET",
    ]
    df = df_full[variables_bsic].copy()

    # Nettoyage
    df["EMPLOI_ANORMAL"] = (df["DAYS_EMPLOYED"] == 365243).astype(int)
    df["DAYS_EMPLOYED"] = df["DAYS_EMPLOYED"].replace(365243, np.nan)
    df["AGE_ANNEES"] = (-df["DAYS_BIRTH"] / 365).round(1)
    df["ANCIENNETE_EMPLOI_ANNEES"] = (-df["DAYS_EMPLOYED"] / 365).round(1)
    df = df.drop(columns=["DAYS_BIRTH", "DAYS_EMPLOYED"])
    df["CODE_GENDER"] = df["CODE_GENDER"].replace("XNA", "F")
    plafond = df["AMT_INCOME_TOTAL"].quantile(0.999)
    df["AMT_INCOME_TOTAL"] = df["AMT_INCOME_TOTAL"].clip(upper=plafond)

    # Separation
    y = df["TARGET"]
    X = df.drop(columns=["TARGET"])
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=GRAINE, stratify=y)

    # Preparateur
    colonnes_num = X_train.select_dtypes(include=[np.number]).columns.tolist()
    colonnes_cat = [c for c in X_train.columns if c not in colonnes_num]
    preparateur = ColumnTransformer([
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median")),
                          ("scaler", StandardScaler())]), colonnes_num),
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                          ("encoder", OneHotEncoder(handle_unknown="ignore",
                                                    sparse_output=False))]), colonnes_cat),
    ])
    return X_train, X_test, y_train, y_test, preparateur


# ---------------------------------------------------------------------------
# 2. Definition des modeles (parametres identiques au notebook)
# ---------------------------------------------------------------------------
def definir_modeles():
    return {
        "Regression logistique": LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=GRAINE),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, max_depth=10, min_samples_leaf=50,
            class_weight="balanced", n_jobs=-1, random_state=GRAINE),
        "Gradient Boosting": LGBMClassifier(
            n_estimators=200, learning_rate=0.05, num_leaves=20,
            class_weight="balanced", n_jobs=-1, random_state=GRAINE, verbose=-1),
    }


def cout_metier(y_vrai, proba, seuil):
    pred = (proba >= seuil).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_vrai, pred).ravel()
    return COUT_FN * fn + COUT_FP * fp


def meilleur_seuil(y_vrai, proba):
    seuils = np.arange(0.05, 0.95, 0.05)
    couts = [cout_metier(y_vrai, proba, s) for s in seuils]
    i = int(np.argmin(couts))
    return round(float(seuils[i]), 2), int(couts[i])


# ---------------------------------------------------------------------------
# 3. Entrainement avec suivi MLflow
# ---------------------------------------------------------------------------
def entrainer_avec_mlflow():
    X_train, X_test, y_train, y_test, preparateur = preparer_donnees()
    modeles = definir_modeles()
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=GRAINE)

    resultats = {}
    for nom, clf in modeles.items():
        # Chaque modele est enregistre dans un "run" MLflow distinct
        with mlflow.start_run(run_name=nom):
            pipe = Pipeline([("prep", preparateur), ("clf", clf)])

            # AUC en validation croisee
            auc_cv = cross_val_score(pipe, X_train, y_train, cv=cv,
                                     scoring="roc_auc", n_jobs=-1).mean()
            # Entrainement final et evaluation sur le test
            pipe.fit(X_train, y_train)
            proba = pipe.predict_proba(X_test)[:, 1]
            auc_test = roc_auc_score(y_test, proba)
            seuil, cout = meilleur_seuil(y_test, proba)

            # --- Enregistrement dans MLflow ---
            # Parametres du modele
            mlflow.log_param("algorithme", nom)
            for param, valeur in clf.get_params().items():
                # on ne logge que les parametres simples
                if isinstance(valeur, (int, float, str, bool, type(None))):
                    mlflow.log_param(param, valeur)
            # Metriques
            mlflow.log_metric("auc_cv", auc_cv)
            mlflow.log_metric("auc_test", auc_test)
            mlflow.log_metric("seuil_optimal", seuil)
            mlflow.log_metric("cout_metier", cout)
            # Le modele lui-meme (pipeline complet)
            mlflow.sklearn.log_model(pipe, name="modele", serialization_format="cloudpickle")

            resultats[nom] = {"pipeline": pipe, "auc_test": auc_test,
                              "seuil": seuil, "cout": cout}
            print("{:<24} AUC(cv)={:.4f} | AUC(test)={:.4f} | cout={} "
                  "-> enregistre dans MLflow".format(nom, auc_cv, auc_test, cout))

    # Selection du meilleur modele (meilleure AUC de test)
    meilleur_nom = max(resultats, key=lambda n: resultats[n]["auc_test"])
    meilleur = resultats[meilleur_nom]["pipeline"]

    # Sauvegarde du meilleur modele en .pkl pour l'API
    joblib.dump(meilleur, "modele_credistore.pkl")

    print()
    print("Meilleur modele :", meilleur_nom,
          "(AUC test = {:.4f})".format(resultats[meilleur_nom]["auc_test"]))
    print("Sauvegarde dans : modele_credistore.pkl")
    print("Toutes les versions sont visibles dans MLflow (http://127.0.0.1:5000)")
    return meilleur_nom


if __name__ == "__main__":
    entrainer_avec_mlflow()
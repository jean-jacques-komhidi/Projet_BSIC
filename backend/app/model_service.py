# -*- coding: utf-8 -*-
"""
Service de modelisation de l'API CREDISCORE.

Charge le modele entraine (.pkl) et fournit :
- le calcul de la probabilite de defaut,
- l'explication de la decision par SHAP (facteurs),
- l'explication en langage naturel destinee a l'agent.
"""

import os
import joblib
import numpy as np
import pandas as pd
import shap
import warnings
warnings.filterwarnings("ignore")

from .explication import generer_explication

SEUIL_DECISION = 0.70

CHEMIN_MODELE = os.path.join(
    os.path.dirname(__file__), "..", "models", "modele_credistore.pkl"
)

COLONNES = [
    "CNT_CHILDREN", "CNT_FAM_MEMBERS", "AMT_INCOME_TOTAL", "AMT_CREDIT",
    "AMT_ANNUITY", "AMT_GOODS_PRICE", "EXT_SOURCE_1", "EXT_SOURCE_2",
    "EXT_SOURCE_3", "EMPLOI_ANORMAL", "AGE_ANNEES", "ANCIENNETE_EMPLOI_ANNEES",
    "CODE_GENDER", "NAME_FAMILY_STATUS", "NAME_EDUCATION_TYPE",
    "OCCUPATION_TYPE", "ORGANIZATION_TYPE", "NAME_INCOME_TYPE",
    "NAME_CONTRACT_TYPE",
]


class ServiceModele:
    """Encapsule le modele et ses operations."""

    def __init__(self, chemin=CHEMIN_MODELE):
        self.pipeline = joblib.load(chemin)
        self.preparateur = self.pipeline.named_steps["prep"]
        self.classifieur = self.pipeline.named_steps["clf"]
        self.explainer = shap.TreeExplainer(self.classifieur)
        self.noms_features = self.preparateur.get_feature_names_out()

    def _dataframe(self, dossier: dict) -> pd.DataFrame:
        return pd.DataFrame([{c: dossier.get(c) for c in COLONNES}])

    def predire(self, dossier: dict) -> float:
        X = self._dataframe(dossier)
        return float(self.pipeline.predict_proba(X)[0, 1])

    def classe_risque(self, proba: float) -> str:
        if proba < 0.40:
            return "faible"
        elif proba < SEUIL_DECISION:
            return "moyen"
        return "eleve"

    def expliquer(self, dossier: dict, top_n=6) -> list:
        """Renvoie les principaux facteurs explicatifs (SHAP)."""
        X = self._dataframe(dossier)
        X_prep = self.preparateur.transform(X)
        valeurs = self.explainer.shap_values(X_prep)
        if isinstance(valeurs, list):
            valeurs = valeurs[1]
        contributions = valeurs[0]

        facteurs = []
        for nom, contrib in zip(self.noms_features, contributions):
            nom_propre = nom.replace("num__", "").replace("cat__", "")
            facteurs.append({"variable": nom_propre, "contribution": float(contrib)})

        facteurs.sort(key=lambda f: abs(f["contribution"]), reverse=True)
        return facteurs[:top_n]

    def analyser(self, dossier: dict) -> dict:
        """Analyse complete : probabilite, classe, decision, facteurs et
        explication en langage naturel."""
        proba = self.predire(dossier)
        decision = "REFUSE" if proba >= SEUIL_DECISION else "ACCORDE"
        facteurs = self.expliquer(dossier)
        explication = generer_explication(decision, facteurs)
        return {
            "probabilite_defaut": round(proba, 4),
            "classe_risque": self.classe_risque(proba),
            "decision": decision,
            "seuil_utilise": SEUIL_DECISION,
            "facteurs_explicatifs": facteurs,
            "explication": explication,
        }
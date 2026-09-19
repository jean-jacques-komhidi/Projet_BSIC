# -*- coding: utf-8 -*-
"""
Service de surveillance de la derive des donnees (data drift).

La derive des donnees survient lorsque les caracteristiques des nouveaux
dossiers s'eloignent de celles sur lesquelles le modele a ete entraine. Le
modele devient alors moins fiable, et un reentrainement peut etre necessaire.

Ce module compare, pour quelques variables cles, la distribution des donnees
recentes (les analyses enregistrees en base) a celle des donnees d'entrainement
(le socle). Il calcule un indicateur de derive (le PSI, Population Stability
Index) et signale les variables qui ont significativement derive.

Interpretation du PSI :
  - < 0,10 : pas de derive significative
  - 0,10 a 0,25 : derive moderee, a surveiller
  - > 0,25 : derive importante, reentrainement recommande
"""

import os
import json
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

from sqlalchemy.orm import Session
from . import models

# Variables numeriques cles a surveiller
VARIABLES_SURVEILLEES = [
    "AMT_INCOME_TOTAL", "AMT_CREDIT", "AMT_ANNUITY",
    "AGE_ANNEES", "ANCIENNETE_EMPLOI_ANNEES",
    "EXT_SOURCE_2", "EXT_SOURCE_3",
]

CHEMIN_CSV = os.path.join(os.path.dirname(__file__), "..", "notebook", "application_train.csv")

# Nombre minimal d'analyses requis pour un calcul de derive fiable
MIN_ANALYSES = 30


def _psi(reference: np.ndarray, actuel: np.ndarray, n_bins=10) -> float:
    """Calcule le Population Stability Index entre deux distributions."""
    # Definir les bornes a partir de la reference
    bornes = np.quantile(reference, np.linspace(0, 1, n_bins + 1))
    bornes[0], bornes[-1] = -np.inf, np.inf
    bornes = np.unique(bornes)
    if len(bornes) < 3:
        return 0.0

    ref_pct = np.histogram(reference, bins=bornes)[0] / len(reference)
    act_pct = np.histogram(actuel, bins=bornes)[0] / len(actuel)
    # Eviter les zeros
    ref_pct = np.where(ref_pct == 0, 0.0001, ref_pct)
    act_pct = np.where(act_pct == 0, 0.0001, act_pct)

    psi = np.sum((act_pct - ref_pct) * np.log(act_pct / ref_pct))
    return float(psi)


def _charger_reference():
    """Charge un echantillon des donnees d'entrainement (le socle)."""
    df = pd.read_csv(CHEMIN_CSV)
    df["AGE_ANNEES"] = (-df["DAYS_BIRTH"] / 365).round(1)
    de = df["DAYS_EMPLOYED"].replace(365243, np.nan)
    df["ANCIENNETE_EMPLOI_ANNEES"] = (-de / 365).round(1)
    return df


def analyser_derive(db: Session) -> dict:
    """Compare les analyses recentes de la base au socle d'entrainement.

    Renvoie un rapport de derive : le PSI par variable, le niveau de derive,
    et une recommandation.
    """
    analyses = db.query(models.Analyse).all()
    nb = len(analyses)

    if nb < MIN_ANALYSES:
        return {
            "statut": "insuffisant",
            "message": (f"Donnees insuffisantes pour analyser la derive "
                        f"({nb} analyses, minimum {MIN_ANALYSES} requis)."),
            "nb_analyses": nb,
        }

    # Extraire les donnees des dossiers analyses
    lignes = []
    for a in analyses:
        if a.donnees_dossier:
            lignes.append(json.loads(a.donnees_dossier))
    if not lignes:
        return {"statut": "insuffisant",
                "message": "Aucune donnee de dossier exploitable.",
                "nb_analyses": nb}

    df_actuel = pd.DataFrame(lignes)
    df_ref = _charger_reference()

    # Calculer le PSI pour chaque variable surveillee
    resultats = {}
    derive_max = 0
    for var in VARIABLES_SURVEILLEES:
        if var in df_actuel.columns and var in df_ref.columns:
            ref = df_ref[var].dropna().values
            act = df_actuel[var].dropna().astype(float).values
            if len(act) > 0 and len(ref) > 0:
                psi = _psi(ref, act)
                if psi < 0.10:
                    niveau = "stable"
                elif psi < 0.25:
                    niveau = "derive moderee"
                else:
                    niveau = "derive importante"
                resultats[var] = {"psi": round(psi, 4), "niveau": niveau}
                derive_max = max(derive_max, psi)

    # Recommandation globale
    if derive_max < 0.10:
        recommandation = "Aucune derive significative. Le modele reste fiable."
    elif derive_max < 0.25:
        recommandation = "Derive moderee detectee. A surveiller."
    else:
        recommandation = "Derive importante detectee. Reentrainement recommande."

    return {
        "statut": "ok",
        "nb_analyses": nb,
        "derive_par_variable": resultats,
        "derive_maximale": round(derive_max, 4),
        "recommandation": recommandation,
    }
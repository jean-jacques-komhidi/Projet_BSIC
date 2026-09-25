# -*- coding: utf-8 -*-
"""
Service de surveillance de la derive des donnees (data drift), version detaillee.

Pour chaque variable surveillee, on compare la distribution des donnees de
production (les analyses recentes) a celle des donnees de reference (le socle
d'entrainement). On calcule :
- la moyenne de reference et la moyenne de production,
- l'ecart relatif en pourcentage,
- un z-score (ecart des moyennes rapporte a l'ecart-type de reference),
- un statut : NORMAL, ALERTE ou CRITIQUE.

Interpretation du z-score :
  - z <= 1   : NORMAL (distribution stable)
  - 1 < z <= 2 : ALERTE (derive moderee)
  - z > 2    : CRITIQUE (derive significative)
"""

import os
import json
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

from sqlalchemy.orm import Session
from . import models

# Variables surveillees, avec leur libelle lisible
VARIABLES = {
    "AMT_INCOME_TOTAL": "Revenu annuel",
    "AMT_CREDIT": "Montant crédit",
    "AMT_ANNUITY": "Mensualité",
    "AGE_ANNEES": "Âge",
    "ANCIENNETE_EMPLOI_ANNEES": "Ancienneté d'emploi",
}

CHEMIN_CSV = os.path.join(os.path.dirname(__file__), "..", "notebook", "application_train.csv")
MIN_ANALYSES = 30


# Cache du socle de reference (calcule une seule fois, garde en memoire)
_reference_cache = None


def _charger_reference():
    """Charge les donnees d'entrainement (le socle) avec les variables derivees.

    Ne charge que les colonnes necessaires (bien plus rapide que tout le CSV)
    et met le resultat en cache pour ne pas relire le fichier a chaque appel.
    """
    global _reference_cache
    if _reference_cache is not None:
        return _reference_cache

    # Ne lire que les colonnes utiles au calcul de derive
    colonnes = ["DAYS_BIRTH", "DAYS_EMPLOYED", "AMT_INCOME_TOTAL",
                "AMT_CREDIT", "AMT_ANNUITY"]
    df = pd.read_csv(CHEMIN_CSV, usecols=colonnes)
    df["AGE_ANNEES"] = (-df["DAYS_BIRTH"] / 365).round(1)
    de = df["DAYS_EMPLOYED"].replace(365243, np.nan)
    df["ANCIENNETE_EMPLOI_ANNEES"] = (-de / 365).round(1)

    # Pre-calculer les moyennes et ecarts-types (ce dont on a besoin)
    _reference_cache = df
    return df


def _statut(z):
    """Determine le statut selon le z-score."""
    if z <= 1:
        return "NORMAL"
    elif z <= 2:
        return "ALERTE"
    return "CRITIQUE"


def analyser_derive(db: Session) -> dict:
    """Compare les analyses recentes au socle et renvoie un rapport detaille."""
    analyses = db.query(models.Analyse).all()
    nb = len(analyses)

    if nb < MIN_ANALYSES:
        return {
            "statut": "insuffisant",
            "message": (f"Donnees insuffisantes pour analyser la derive "
                        f"({nb} analyses, minimum {MIN_ANALYSES} requis)."),
            "nb_analyses": nb,
        }

    # Extraire les donnees de production (les dossiers analyses)
    lignes = []
    for a in analyses:
        if a.donnees_dossier:
            lignes.append(json.loads(a.donnees_dossier))
    if not lignes:
        return {"statut": "insuffisant", "message": "Aucune donnee exploitable.", "nb_analyses": nb}

    df_prod = pd.DataFrame(lignes)
    df_ref = _charger_reference()

    features = []
    z_max = 0
    for var, libelle in VARIABLES.items():
        if var not in df_prod.columns or var not in df_ref.columns:
            continue
        ref = df_ref[var].dropna().astype(float)
        prod = df_prod[var].dropna().astype(float)
        if len(ref) == 0 or len(prod) == 0:
            continue

        ref_mean = float(ref.mean())
        prod_mean = float(prod.mean())
        ref_std = float(ref.std()) or 1.0

        # Ecart relatif en %
        ecart_pct = round(abs(prod_mean - ref_mean) / (abs(ref_mean) or 1) * 100, 1)
        # Z-score : ecart des moyennes rapporte a l'ecart-type de reference
        z = round(abs(prod_mean - ref_mean) / ref_std, 2)
        statut = _statut(z)
        z_max = max(z_max, z)

        features.append({
            "feature": libelle,
            "variable": var,
            "statut": statut,
            "ecart_pct": ecart_pct,
            "z_score": z,
            "ref_mean": round(ref_mean),
            "prod_mean": round(prod_mean),
        })

    # Statut global
    critique = any(f["statut"] == "CRITIQUE" for f in features)
    alerte = any(f["statut"] == "ALERTE" for f in features)
    if critique:
        recommandation = "Drift critique — Reentrainement recommande !"
    elif alerte:
        recommandation = "Derive moderee detectee sur certaines variables."
    else:
        recommandation = "Aucune derive detectee — Distribution normale."

    return {
        "statut": "ok",
        "nb_analyses": nb,
        "total_predictions": nb,
        "drift_features": features,
        "z_max": z_max,
        "recommandation": recommandation,
    }
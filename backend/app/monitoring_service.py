# -*- coding: utf-8 -*-
"""
Service de monitoring : lecture des experiences MLflow et etat du reentrainement.

Ce module lit les runs enregistres dans MLflow (via son API de tracking) pour
les afficher dans la page de monitoring, et gere l'etat du reentrainement
asynchrone (progression en temps reel).
"""

import os

# Adresse du serveur MLflow
MLFLOW_URI = "http://127.0.0.1:5000"
EXPERIENCE = "CREDISCORE_BSIC"


# Cache leger des runs MLflow (quelques secondes), pour eviter de reinterroger
# le serveur MLflow a chaque ouverture de la page
import time
_runs_cache = {"data": None, "time": 0}
_CACHE_DUREE = 10  # secondes


def get_mlflow_runs():
    """Lit les runs MLflow de l'experience et renvoie une liste synthetique.

    Renvoie une liste de dictionnaires : modele, auc_roc, score_metier, run_id, statut.
    Les runs sont tries par AUC decroissant (le meilleur en premier).
    """
    # Servir depuis le cache si recent
    global _runs_cache
    if _runs_cache["data"] is not None and (time.time() - _runs_cache["time"]) < _CACHE_DUREE:
        return _runs_cache["data"]

    try:
        import mlflow
        mlflow.set_tracking_uri(MLFLOW_URI)
        client = mlflow.tracking.MlflowClient()

        # Trouver l'experience
        experience = client.get_experiment_by_name(EXPERIENCE)
        if experience is None:
            return []

        # Recuperer les runs
        runs = client.search_runs(
            experiment_ids=[experience.experiment_id],
            order_by=["metrics.auc_test DESC"],
            max_results=20,
        )

        resultat = []
        for run in runs:
            metriques = run.data.metrics
            params = run.data.params
            auc = metriques.get("auc_test") or metriques.get("auc_cv")
            resultat.append({
                "run_id": run.info.run_id[:8],
                "modele": params.get("algorithme", run.info.run_name or "Modele"),
                "auc_roc": round(auc, 4) if auc else None,
                "score_metier": int(metriques["cout_metier"]) if "cout_metier" in metriques else None,
                "statut": "termine",
            })
        _runs_cache = {"data": resultat, "time": time.time()}
        return resultat
    except Exception:
        # MLflow indisponible ou erreur : renvoyer une liste vide
        return []
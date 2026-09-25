# -*- coding: utf-8 -*-
"""
Gestionnaire du reentrainement asynchrone.

Le reentrainement etant une operation longue, on l'execute dans un thread de
fond et on expose son etat (en cours, progression, message, resultat) via un
objet partage. La page de monitoring interroge regulierement cet etat pour
afficher la progression en temps reel.
"""

import threading
import json
from datetime import datetime

# Etat global du reentrainement (partage entre les requetes)
etat_retrain = {
    "running": False,
    "progress": 0,
    "message": "",
    "last_result": None,
    "current_version": "1.0",
}

_lock = threading.Lock()


def _executer_reentrainement(db_factory):
    """Execute le reentrainement en tache de fond, en mettant a jour l'etat."""
    from .reentrainement import reentrainer
    from . import models

    db = db_factory()
    try:
        with _lock:
            etat_retrain["running"] = True
            etat_retrain["progress"] = 10
            etat_retrain["message"] = "Chargement des donnees..."

        # AUC de l'ancien modele en production (avant)
        ancienne = db.query(models.ModelVersion).filter(
            models.ModelVersion.en_production == True).first()
        ancien_auc = ancienne.auc if ancienne else None

        with _lock:
            etat_retrain["progress"] = 40
            etat_retrain["message"] = "Reentrainement des modeles..."

        # Lancer le reentrainement (fonction existante)
        resume = reentrainer(db, avec_mlflow=True)

        with _lock:
            etat_retrain["progress"] = 90
            etat_retrain["message"] = "Finalisation..."

        nouveau_auc = resume["auc_test"]
        ameliore = ancien_auc is None or nouveau_auc >= ancien_auc

        # Notification
        try:
            from .notification_service import creer_notification
            creer_notification(
                db, titre="Reentrainement termine",
                message=f"Meilleur modele : {resume['meilleur_modele']} (AUC {nouveau_auc}).",
                type="succes")
        except Exception:
            pass

        with _lock:
            etat_retrain["progress"] = 100
            etat_retrain["running"] = False
            etat_retrain["message"] = "Reentrainement termine."
            etat_retrain["current_version"] = str(resume.get("total_donnees", "1.0"))
            etat_retrain["last_result"] = {
                "improved": ameliore,
                "best_model": resume["meilleur_modele"],
                "old_auc": round(ancien_auc, 4) if ancien_auc else None,
                "new_auc": nouveau_auc,
                "new_version": resume.get("total_donnees"),
                "donnees_reelles": resume.get("donnees_reelles_integrees", 0),
                "total_donnees": resume.get("total_donnees"),
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
            }
    except Exception as e:
        with _lock:
            etat_retrain["running"] = False
            etat_retrain["progress"] = 0
            etat_retrain["message"] = f"Erreur : {e}"
    finally:
        db.close()


def lancer_reentrainement(db_factory):
    """Demarre le reentrainement en tache de fond (si pas deja en cours)."""
    with _lock:
        if etat_retrain["running"]:
            return False
        etat_retrain["running"] = True
        etat_retrain["progress"] = 0
        etat_retrain["message"] = "Demarrage..."
        etat_retrain["last_result"] = None

    thread = threading.Thread(target=_executer_reentrainement, args=(db_factory,), daemon=True)
    thread.start()
    return True


def get_etat():
    """Renvoie l'etat actuel du reentrainement."""
    with _lock:
        return dict(etat_retrain)
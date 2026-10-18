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
from datetime import datetime, timedelta

# Etat global du reentrainement (partage entre les requetes)
etat_retrain = {
    "running": False,
    "progress": 0,
    "message": "",
    "last_result": None,
}

_lock = threading.Lock()


def _texte_resultat(resume) -> str:
    def f(x):
        return f"{x:.3f}".replace(".", ",") if x is not None else "inconnue"
    return (f"Candidat {resume['meilleur_modele']} : AUC {f(resume['auc_candidat'])} contre {f(resume['auc_actuel'])} "
            f"pour le modèle en service, sur le {resume['jeu_comparaison']}.")


def _executer_reentrainement(db_factory, auteur=None):
    """Execute le reentrainement en tache de fond, en mettant a jour l'etat."""
    from .reentrainement import reentrainer
    from .notification_service import notifier_admins, notifier_agents

    db = db_factory()
    try:
        with _lock:
            etat_retrain["running"] = True
            etat_retrain["progress"] = 20
            etat_retrain["message"] = "Chargement des données et entraînement des modèles..."

        resume = reentrainer(db, avec_mlflow=True, auteur=auteur)

        with _lock:
            etat_retrain["progress"] = 90
            etat_retrain["message"] = "Finalisation..."

        lien = {"categorie": "modele", "lien": "/monitoring", "texte_lien": "Ouvrir le monitoring"}
        if resume["promu"]:
            notifier_admins(db, "Nouveau modèle mis en service",
                            _texte_resultat(resume) + " Il fait mieux et remplace le modèle précédent.",
                            type="succes", **lien)
            notifier_agents(db, "Le modèle de scoring a été mis à jour",
                            "Une nouvelle version est en service. Un même profil peut obtenir un score "
                            "légèrement différent de celui d'avant.", type="info", categorie="modele")
        else:
            notifier_admins(db, "Nouveau modèle non retenu",
                            _texte_resultat(resume) + " Il ne fait pas mieux : le modèle en service est conservé.",
                            type="info", **lien)

        with _lock:
            etat_retrain["progress"] = 100
            etat_retrain["running"] = False
            etat_retrain["message"] = "Réentraînement terminé."
            etat_retrain["last_result"] = {
                "improved": resume["promu"],
                "best_model": resume["meilleur_modele"],
                "old_auc": resume["auc_actuel"],
                "new_auc": resume["auc_candidat"],
                "jeu_comparaison": resume["jeu_comparaison"],
                "donnees_reelles": resume.get("donnees_reelles_integrees", 0),
                "total_donnees": resume.get("total_donnees"),
                "timestamp": (datetime.utcnow() + timedelta(hours=1)).strftime("%d/%m/%Y %H:%M"),
            }
    except Exception as e:
        with _lock:
            etat_retrain["running"] = False
            etat_retrain["progress"] = 0
            etat_retrain["message"] = f"Erreur : {e}"
    finally:
        db.close()


def lancer_reentrainement(db_factory, auteur=None):
    """Demarre le reentrainement en tache de fond (si pas deja en cours)."""
    with _lock:
        if etat_retrain["running"]:
            return False
        etat_retrain["running"] = True
        etat_retrain["progress"] = 0
        etat_retrain["message"] = "Demarrage..."
        etat_retrain["last_result"] = None

    thread = threading.Thread(target=_executer_reentrainement, args=(db_factory, auteur), daemon=True)
    thread.start()
    return True


def get_etat():
    """Renvoie l'etat actuel du reentrainement."""
    with _lock:
        return dict(etat_retrain)
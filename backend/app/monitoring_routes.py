# -*- coding: utf-8 -*-
"""
Routes de monitoring (reserve a l'administrateur).

  - GET  /monitoring/etat            : etat complet du modele (donnees, predictions,
                                       performance reelle, regle) et versions
  - POST /monitoring/retrain         : lancer le reentrainement (asynchrone)
  - GET  /monitoring/retrain/status  : etat du reentrainement (progression)
  - GET  /monitoring/mlflow          : les runs MLflow, si le serveur MLflow tourne
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .database import get_db, SessionLocal
from . import models
from .security import administrateur_courant
from .monitoring_service import get_mlflow_runs
from .retrain_manager import lancer_reentrainement, get_etat
from .surveillance_service import etat_du_modele, liste_versions
from .alertes_service import verifier_et_notifier

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/etat")
def etat(
    db: Session = Depends(get_db),
    admin: models.User = Depends(administrateur_courant),
):
    """Etat du modele. Profite de la visite pour lancer la verification du jour."""
    calcule = verifier_et_notifier(db)
    resultat = calcule or etat_du_modele(db)
    resultat["versions"] = liste_versions(db, resultat["performance"]["auc"])
    resultat["reentrainement"] = get_etat()
    return resultat


@router.get("/mlflow")
def runs_mlflow(admin: models.User = Depends(administrateur_courant)):
    """Renvoie les runs MLflow (modeles entraines et leurs performances)."""
    return get_mlflow_runs()


@router.post("/retrain")
def lancer_retrain(admin: models.User = Depends(administrateur_courant)):
    """Lance le reentrainement en tache de fond."""
    demarre = lancer_reentrainement(SessionLocal, auteur=admin.nom)
    if not demarre:
        return {"message": "Un reentrainement est deja en cours."}
    return {"message": "Reentrainement lance."}


@router.get("/retrain/status")
def statut_retrain(admin: models.User = Depends(administrateur_courant)):
    """Renvoie l'etat du reentrainement (en cours, progression, resultat)."""
    return get_etat()

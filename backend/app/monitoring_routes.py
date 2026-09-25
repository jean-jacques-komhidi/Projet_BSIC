# -*- coding: utf-8 -*-
"""
Routes de monitoring (reserve a l'administrateur).

  - GET  /monitoring/mlflow          : les runs MLflow (modeles entraines)
  - POST /monitoring/retrain         : lancer le reentrainement (asynchrone)
  - GET  /monitoring/retrain/status  : etat du reentrainement (progression)
  - GET  /monitoring/drift           : analyse de la derive des donnees
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .database import get_db, SessionLocal
from . import models
from .security import administrateur_courant
from .monitoring_service import get_mlflow_runs
from .retrain_manager import lancer_reentrainement, get_etat
from .drift_service import analyser_derive

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/mlflow")
def runs_mlflow(admin: models.User = Depends(administrateur_courant)):
    """Renvoie les runs MLflow (modeles entraines et leurs performances)."""
    return get_mlflow_runs()


@router.post("/retrain")
def lancer_retrain(admin: models.User = Depends(administrateur_courant)):
    """Lance le reentrainement en tache de fond."""
    demarre = lancer_reentrainement(SessionLocal)
    if not demarre:
        return {"message": "Un reentrainement est deja en cours."}
    return {"message": "Reentrainement lance."}


@router.get("/retrain/status")
def statut_retrain(admin: models.User = Depends(administrateur_courant)):
    """Renvoie l'etat du reentrainement (en cours, progression, resultat)."""
    return get_etat()


@router.get("/drift")
def drift(
    db: Session = Depends(get_db),
    admin: models.User = Depends(administrateur_courant),
):
    """Analyse la derive des donnees."""
    return analyser_derive(db)
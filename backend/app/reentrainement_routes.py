# -*- coding: utf-8 -*-
"""
Route de reentrainement du modele.

  - POST /reentrainer : declenche le reentrainement (reserve a l'administrateur)

Le reentrainement combine le socle historique et les analyses reelles resolues
de la base, reentraine les trois modeles, selectionne le meilleur, le met en
production et enregistre le tout dans MLflow.

Attention : l'operation est longue (plusieurs minutes). La reponse n'arrive
qu'une fois le reentrainement termine.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .security import administrateur_courant
from .reentrainement import reentrainer
from .model_service import ServiceModele

router = APIRouter(prefix="/reentrainer", tags=["Reentrainement"])


@router.post("")
def lancer_reentrainement(
    db: Session = Depends(get_db),
    admin: models.User = Depends(administrateur_courant),
):
    """Declenche le reentrainement du modele. Reserve a l'administrateur.

    Renvoie un resume : le meilleur modele retenu, sa performance, et le nombre
    de donnees reelles integrees depuis la base.
    """
    resume = reentrainer(db, avec_mlflow=True)

    # Recharger le modele fraichement entraine dans le service utilise par l'API
    # pour que les analyses suivantes utilisent la nouvelle version.
    import app.model_service as ms
    import app.analyse_routes as ar
    nouveau_service = ServiceModele()
    ms_instance = nouveau_service
    ar.service = nouveau_service

    return {
        "message": "Reentrainement termine avec succes",
        "resultat": resume,
    }
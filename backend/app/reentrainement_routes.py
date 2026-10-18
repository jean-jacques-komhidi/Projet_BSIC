# -*- coding: utf-8 -*-
"""
Route de reentrainement du modele.

  - POST /reentrainer : declenche le reentrainement (reserve a l'administrateur)

Le reentrainement combine le socle historique et les analyses reelles resolues
de la base, reentraine les trois modeles et retient le meilleur comme candidat.
Le candidat n'est mis en service que s'il bat le modele actuel sur les memes
donnees ; tout est enregistre dans MLflow.

Attention : l'operation est longue (plusieurs minutes). La reponse n'arrive
qu'une fois le reentrainement termine.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .security import administrateur_courant
from .reentrainement import reentrainer
from .notification_service import notifier_admins

router = APIRouter(prefix="/reentrainer", tags=["Reentrainement"])


@router.post("")
def lancer_reentrainement(
    db: Session = Depends(get_db),
    admin: models.User = Depends(administrateur_courant),
):
    """Declenche le reentrainement (attend la fin). Reserve a l'administrateur.

    Le candidat n'est mis en service que s'il fait mieux que le modele actuel ;
    le modele est alors recharge immediatement."""
    try:
        resume = reentrainer(db, avec_mlflow=True, auteur=admin.nom)
    except FileNotFoundError as e:
        raise HTTPException(status_code=409, detail=str(e))
    notifier_admins(
        db, "Nouveau modèle mis en service" if resume["promu"] else "Nouveau modèle non retenu",
        f"Candidat {resume['meilleur_modele']} : AUC {resume['auc_candidat']} contre {resume['auc_actuel']} "
        f"pour le modèle en service ({resume['jeu_comparaison']}).",
        type="succes" if resume["promu"] else "info", categorie="modele",
        lien="/monitoring", texte_lien="Ouvrir le monitoring")
    return {"message": "Reentrainement termine", "resultat": resume}

# -*- coding: utf-8 -*-
"""
Routes des notifications.

  - GET  /notifications              : lister les notifications
  - GET  /notifications/non-lues     : compter les notifications non lues
  - PUT  /notifications/{id}/lue     : marquer une notification comme lue
  - PUT  /notifications/tout-lu      : marquer toutes comme lues

Accessible a tout utilisateur connecte.
"""

from pydantic import BaseModel
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .security import utilisateur_courant

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationReponse(BaseModel):
    id: int
    titre: str
    message: str
    type: str
    lue: bool
    date_creation: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[NotificationReponse])
def lister_notifications(
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Liste les notifications, les plus recentes d'abord."""
    return db.query(models.Notification).order_by(
        models.Notification.date_creation.desc()).limit(50).all()


@router.get("/non-lues")
def compter_non_lues(
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Compte les notifications non lues (pour le badge de la cloche)."""
    nombre = db.query(models.Notification).filter(
        models.Notification.lue == False).count()
    return {"non_lues": nombre}


@router.put("/{notif_id}/lue")
def marquer_lue(
    notif_id: int,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Marque une notification comme lue."""
    notif = db.query(models.Notification).filter(
        models.Notification.id == notif_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification introuvable")
    notif.lue = True
    db.commit()
    return {"message": "Notification marquee comme lue"}


@router.put("/tout-lu")
def tout_marquer_lu(
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Marque toutes les notifications comme lues."""
    db.query(models.Notification).filter(
        models.Notification.lue == False).update({models.Notification.lue: True})
    db.commit()
    return {"message": "Toutes les notifications marquees comme lues"}
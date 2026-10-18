# -*- coding: utf-8 -*-
"""
Routes des notifications.

  - GET  /notifications              : lister mes notifications
  - GET  /notifications/non-lues     : compter mes notifications non lues
  - PUT  /notifications/{id}/lue     : marquer une de mes notifications comme lue
  - PUT  /notifications/tout-lu      : marquer toutes mes notifications comme lues

Chaque personne ne voit que ses propres notifications. Les anciennes
notifications sans destinataire sont reservees aux administrateurs.
"""

from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
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
    categorie: Optional[str] = None
    lien: Optional[str] = None
    texte_lien: Optional[str] = None

    class Config:
        from_attributes = True


def _mes_notifications(db: Session, utilisateur):
    condition = models.Notification.destinataire_id == utilisateur.id
    if utilisateur.role == "admin":
        condition = or_(condition, models.Notification.destinataire_id.is_(None))
    return db.query(models.Notification).filter(condition)


@router.get("", response_model=list[NotificationReponse])
def lister_notifications(
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Liste mes notifications, les plus recentes d'abord."""
    return _mes_notifications(db, utilisateur).order_by(
        models.Notification.date_creation.desc()).limit(50).all()


@router.get("/non-lues")
def compter_non_lues(
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Compte mes notifications non lues (pour le badge de la cloche)."""
    nombre = _mes_notifications(db, utilisateur).filter(models.Notification.lue == False).count()  # noqa: E712
    return {"non_lues": nombre}


@router.put("/{notif_id}/lue")
def marquer_lue(
    notif_id: int,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Marque une de mes notifications comme lue."""
    notif = _mes_notifications(db, utilisateur).filter(models.Notification.id == notif_id).first()
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
    """Marque toutes mes notifications comme lues (sans toucher a celles des autres)."""
    for notif in _mes_notifications(db, utilisateur).filter(models.Notification.lue == False).all():  # noqa: E712
        notif.lue = True
    db.commit()
    return {"message": "Toutes les notifications marquees comme lues"}

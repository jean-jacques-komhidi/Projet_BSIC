# -*- coding: utf-8 -*-
"""
Service de gestion des notifications.

Fournit une fonction simple pour creer une notification lors d'un evenement
important de l'application (reentrainement, detection de derive, etc.).
"""

from sqlalchemy.orm import Session
from . import models


def creer_notification(db: Session, titre: str, message: str, type: str = "info"):
    """Cree une notification en base.

    - type : 'info', 'succes' ou 'alerte' (pour l'affichage cote frontend)
    """
    notif = models.Notification(titre=titre, message=message, type=type)
    db.add(notif)
    db.commit()
    return notif
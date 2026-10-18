# -*- coding: utf-8 -*-
"""
Service de gestion des notifications.

Chaque notification a un destinataire : chaque personne voit les siennes et
les marque comme lues sans effet sur les autres. Les fonctions ci-dessous
permettent de prevenir une personne, tous les administrateurs ou tout le monde.

Types (couleur affichee) :
  - 'danger' : action urgente (rouge)
  - 'alerte' : a surveiller (orange)
  - 'info'   : information (bleu)
  - 'succes' : evenement positif (vert)
"""

from sqlalchemy.orm import Session
from . import models


def creer_notification(db: Session, titre: str, message: str, type: str = "info",
                       destinataire_id: int = None, categorie: str = None,
                       lien: str = None, texte_lien: str = None, valider: bool = True):
    """Cree une notification pour une personne (ou, sans destinataire, pour les admins)."""
    notif = models.Notification(
        titre=titre, message=message, type=type, destinataire_id=destinataire_id,
        categorie=categorie, lien=lien, texte_lien=texte_lien)
    db.add(notif)
    if valider:
        db.commit()
    return notif


def notifier_admins(db: Session, titre: str, message: str, **options):
    """Une notification par administrateur (chacun a son propre statut lu)."""
    admins = db.query(models.User).filter(models.User.role == "admin").all()
    for admin in admins:
        creer_notification(db, titre, message, destinataire_id=admin.id, valider=False, **options)
    db.commit()
    return len(admins)


def notifier_agents(db: Session, titre: str, message: str, **options):
    """Une notification par agent de credit."""
    agents = db.query(models.User).filter(models.User.role != "admin").all()
    for agent in agents:
        creer_notification(db, titre, message, destinataire_id=agent.id, valider=False, **options)
    db.commit()
    return len(agents)

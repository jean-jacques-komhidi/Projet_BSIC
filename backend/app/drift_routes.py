# -*- coding: utf-8 -*-
"""
Route de surveillance de la derive des donnees (data drift).

  - GET /drift : analyse la derive des donnees (reserve a l'admin)

Compare les analyses recentes au socle d'entrainement et signale une
eventuelle derive, avec une recommandation de reentrainement.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .security import administrateur_courant
from .drift_service import analyser_derive
from .notification_service import creer_notification

router = APIRouter(prefix="/drift", tags=["Surveillance (data drift)"])


@router.get("")
def surveiller_derive(
    db: Session = Depends(get_db),
    admin: models.User = Depends(administrateur_courant),
):
    """Analyse la derive des donnees. Reserve a l'administrateur."""
    resultat = analyser_derive(db)
    # Si une derive importante est detectee, creer une notification d'alerte
    if resultat.get("statut") == "ok" and resultat.get("derive_maximale", 0) >= 0.25:
        creer_notification(
            db,
            titre="Derive importante detectee",
            message=f"Une derive importante des donnees a ete detectee "
                    f"(indice {resultat['derive_maximale']}). Un reentrainement est recommande.",
            type="alerte",
        )
    return resultat
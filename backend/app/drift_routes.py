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

router = APIRouter(prefix="/drift", tags=["Surveillance (data drift)"])


@router.get("")
def surveiller_derive(
    db: Session = Depends(get_db),
    admin: models.User = Depends(administrateur_courant),
):
    """Analyse la derive des donnees. Reserve a l'administrateur."""
    return analyser_derive(db)
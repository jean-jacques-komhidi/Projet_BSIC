# -*- coding: utf-8 -*-
"""
Schemas de donnees lies aux analyses de credit enregistrees.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from .schemas import DossierCredit


class AnalyseCreation(BaseModel):
    """Donnees pour realiser et enregistrer une analyse."""
    client_id: int = Field(..., description="Identifiant du client concerne")
    dossier: DossierCredit = Field(..., description="Donnees du dossier de credit")


class AnalyseReponse(BaseModel):
    """Representation d'une analyse enregistree, renvoyee par l'API."""
    id: int
    client_id: Optional[int] = None
    user_id: Optional[int] = None
    nom_client: Optional[str] = None
    probabilite_defaut: float
    classe_risque: Optional[str] = None
    decision: Optional[str] = None
    explication: Optional[str] = None
    facteurs_explicatifs: Optional[Any] = None   # liste de facteurs SHAP (decodee)
    resultat_reel: Optional[str] = None
    model_version_id: Optional[int] = None
    date_analyse: datetime

    class Config:
        from_attributes = True
# -*- coding: utf-8 -*-
"""
Schemas de donnees lies aux clients (demandeurs de credit).

Le client represente l'identite du demandeur (nom, genre, age, profession,
situation familiale). Les donnees financieres (revenu, montant du credit,
scores, etc.) sont saisies au moment de l'analyse, car elles sont propres
a chaque demande et peuvent varier dans le temps.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ClientCreation(BaseModel):
    """Donnees pour creer un nouveau client."""
    nom: str = Field(..., description="Nom complet du client")
    genre: Optional[str] = Field(None, description="Genre : 'M' ou 'F'")
    age: Optional[float] = Field(None, ge=18, le=100, description="Age du client")
    profession: Optional[str] = Field(None, description="Profession")
    situation_familiale: Optional[str] = Field(None, description="Situation familiale")


class ClientModification(BaseModel):
    """Donnees pour modifier un client. Seuls les champs fournis sont modifies."""
    nom: Optional[str] = None
    genre: Optional[str] = None
    age: Optional[float] = Field(None, ge=18, le=100)
    profession: Optional[str] = None
    situation_familiale: Optional[str] = None


class ClientReponse(BaseModel):
    """Representation d'un client renvoyee par l'API."""
    id: int
    nom: str
    genre: Optional[str] = None
    age: Optional[float] = None
    profession: Optional[str] = None
    situation_familiale: Optional[str] = None
    date_creation: datetime

    class Config:
        from_attributes = True
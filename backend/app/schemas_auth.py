# -*- coding: utf-8 -*-
"""
Schemas de donnees lies a l'authentification et aux utilisateurs.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UtilisateurCreation(BaseModel):
    """Donnees pour creer un nouvel utilisateur."""
    nom: str = Field(..., description="Nom de l'utilisateur")
    email: EmailStr = Field(..., description="Adresse e-mail (identifiant de connexion)")
    mot_de_passe: str = Field(..., min_length=6, description="Mot de passe (6 caracteres minimum)")
    role: str = Field("agent", description="Role : 'agent' ou 'admin'")


class UtilisateurModification(BaseModel):
    """Donnees pour modifier un utilisateur. Tous les champs sont optionnels :
    seuls ceux fournis seront modifies."""
    nom: Optional[str] = None
    email: Optional[EmailStr] = None
    mot_de_passe: Optional[str] = Field(None, min_length=6)
    role: Optional[str] = None


class UtilisateurReponse(BaseModel):
    """Representation d'un utilisateur renvoyee par l'API (sans mot de passe)."""
    id: int
    nom: str
    email: EmailStr
    role: str

    class Config:
        from_attributes = True


class Jeton(BaseModel):
    """Jeton d'acces renvoye apres une connexion reussie."""
    access_token: str
    token_type: str = "bearer"
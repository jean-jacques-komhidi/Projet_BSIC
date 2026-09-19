# -*- coding: utf-8 -*-
"""
Routes d'authentification et de gestion des utilisateurs (CRUD complet).

Regroupe :
  Authentification
    - POST /auth/connexion         : se connecter, obtenir un jeton
    - GET  /auth/moi               : consulter ses propres informations
  Gestion des utilisateurs (CRUD)
    - POST   /auth/utilisateurs        : creer un utilisateur (Create)
    - GET    /auth/utilisateurs        : lister les utilisateurs (Read)
    - GET    /auth/utilisateurs/{id}   : voir un utilisateur (Read)
    - PUT    /auth/utilisateurs/{id}   : modifier un utilisateur (Update)
    - DELETE /auth/utilisateurs/{id}   : supprimer un utilisateur (Delete)

La creation du tout premier utilisateur est libre (pour amorcer le systeme) ;
au-dela, lister, modifier et supprimer sont reserves a l'administrateur.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .schemas_auth import (
    UtilisateurCreation, UtilisateurModification,
    UtilisateurReponse, Jeton,
)
from .security import (
    hacher_mot_de_passe, verifier_mot_de_passe, creer_jeton,
    utilisateur_courant, administrateur_courant,
)

router = APIRouter(prefix="/auth", tags=["Authentification et utilisateurs"])


# ===========================================================================
# AUTHENTIFICATION
# ===========================================================================
@router.post("/connexion", response_model=Jeton)
def connexion(
    identifiants: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Connecte un utilisateur et renvoie un jeton d'acces.

    L'e-mail est envoye dans le champ 'username', le mot de passe dans 'password'.
    """
    utilisateur = db.query(models.User).filter(
        models.User.email == identifiants.username
    ).first()

    if not utilisateur or not verifier_mot_de_passe(
        identifiants.password, utilisateur.mot_de_passe
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jeton = creer_jeton({"sub": utilisateur.email, "role": utilisateur.role})
    return {"access_token": jeton, "token_type": "bearer"}


@router.get("/moi", response_model=UtilisateurReponse)
def mes_informations(utilisateur: models.User = Depends(utilisateur_courant)):
    """Renvoie les informations de l'utilisateur actuellement connecte."""
    return utilisateur


# ===========================================================================
# CRUD DES UTILISATEURS
# ===========================================================================

# --- CREATE : creer un utilisateur ---
@router.post("/utilisateurs", response_model=UtilisateurReponse, status_code=201)
def creer_utilisateur(donnees: UtilisateurCreation, db: Session = Depends(get_db)):
    """Cree un nouvel utilisateur.

    Verifie que l'e-mail est libre, hache le mot de passe, puis enregistre.
    La creation reste ouverte pour permettre d'amorcer le premier compte ;
    dans une version ulterieure, on pourra la reserver a l'administrateur.
    """
    existant = db.query(models.User).filter(models.User.email == donnees.email).first()
    if existant:
        raise HTTPException(status_code=400, detail="Cet e-mail est deja utilise")

    if donnees.role not in ("agent", "admin"):
        raise HTTPException(status_code=400, detail="Role invalide (agent ou admin)")

    utilisateur = models.User(
        nom=donnees.nom,
        email=donnees.email,
        mot_de_passe=hacher_mot_de_passe(donnees.mot_de_passe),
        role=donnees.role,
    )
    db.add(utilisateur)
    db.commit()
    db.refresh(utilisateur)
    return utilisateur


# --- READ : lister tous les utilisateurs (admin) ---
@router.get("/utilisateurs", response_model=list[UtilisateurReponse])
def lister_utilisateurs(
    db: Session = Depends(get_db),
    admin: models.User = Depends(administrateur_courant),
):
    """Liste tous les utilisateurs. Reserve a l'administrateur."""
    return db.query(models.User).all()


# --- READ : voir un utilisateur precis (admin) ---
@router.get("/utilisateurs/{user_id}", response_model=UtilisateurReponse)
def voir_utilisateur(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(administrateur_courant),
):
    """Renvoie un utilisateur precis. Reserve a l'administrateur."""
    utilisateur = db.query(models.User).filter(models.User.id == user_id).first()
    if not utilisateur:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return utilisateur


# --- UPDATE : modifier un utilisateur (admin) ---
@router.put("/utilisateurs/{user_id}", response_model=UtilisateurReponse)
def modifier_utilisateur(
    user_id: int,
    donnees: UtilisateurModification,
    db: Session = Depends(get_db),
    admin: models.User = Depends(administrateur_courant),
):
    """Modifie un utilisateur (nom, e-mail, role, mot de passe).

    Seuls les champs fournis sont modifies. Reserve a l'administrateur.
    """
    utilisateur = db.query(models.User).filter(models.User.id == user_id).first()
    if not utilisateur:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if donnees.nom is not None:
        utilisateur.nom = donnees.nom
    if donnees.email is not None:
        # verifier que le nouvel e-mail n'est pas deja pris par un autre
        autre = db.query(models.User).filter(
            models.User.email == donnees.email,
            models.User.id != user_id,
        ).first()
        if autre:
            raise HTTPException(status_code=400, detail="Cet e-mail est deja utilise")
        utilisateur.email = donnees.email
    if donnees.role is not None:
        if donnees.role not in ("agent", "admin"):
            raise HTTPException(status_code=400, detail="Role invalide")
        utilisateur.role = donnees.role
    if donnees.mot_de_passe is not None:
        utilisateur.mot_de_passe = hacher_mot_de_passe(donnees.mot_de_passe)

    db.commit()
    db.refresh(utilisateur)
    return utilisateur


# --- DELETE : supprimer un utilisateur (admin) ---
@router.delete("/utilisateurs/{user_id}", status_code=200)
def supprimer_utilisateur(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(administrateur_courant),
):
    """Supprime un utilisateur. Reserve a l'administrateur.

    Un administrateur ne peut pas se supprimer lui-meme (securite).
    """
    utilisateur = db.query(models.User).filter(models.User.id == user_id).first()
    if not utilisateur:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if utilisateur.id == admin.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas vous supprimer vous-meme")

    db.delete(utilisateur)
    db.commit()
    return {"message": "Utilisateur supprime", "id": user_id}
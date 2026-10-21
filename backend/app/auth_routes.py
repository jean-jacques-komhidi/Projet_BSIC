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

Toute la gestion des utilisateurs (creer, lister, modifier, supprimer) est
reservee a l'administrateur. Le tout premier administrateur est cree par le
script app/creer_admin.py, jamais par une route publique.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, EmailStr

from .database import get_db
from . import models
from .schemas_auth import (
    UtilisateurCreation, UtilisateurModification,
    UtilisateurReponse, Jeton,
)
from .security import (
    hacher_mot_de_passe, verifier_mot_de_passe, creer_jeton,
    utilisateur_courant, administrateur_courant,
    valider_mot_de_passe, message_mot_de_passe,
)

DECALAGE_TCHAD = timedelta(hours=1)


def _verifier_regles(mot_de_passe, nom, email):
    erreurs = valider_mot_de_passe(mot_de_passe, nom, email)
    if erreurs:
        raise HTTPException(status_code=400, detail=message_mot_de_passe(erreurs))

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


@router.put("/moi", response_model=UtilisateurReponse)
def modifier_mes_informations(
    donnees: UtilisateurModification,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Permet a l'utilisateur connecte de modifier son nom.

    L'e-mail (identifiant de connexion) et le role sont geres par
    l'administrateur ; le mot de passe se change par /auth/moi/mot-de-passe,
    qui exige l'ancien mot de passe."""
    if donnees.email is not None and donnees.email != utilisateur.email:
        raise HTTPException(status_code=403, detail="L'adresse e-mail est modifiée par l'administrateur.")
    if donnees.mot_de_passe is not None:
        raise HTTPException(status_code=400, detail="Changez votre mot de passe depuis la rubrique Mot de passe.")
    if donnees.nom is not None:
        nom = donnees.nom.strip()
        if not 2 <= len(nom) <= 100:
            raise HTTPException(status_code=400, detail="Le nom doit faire entre 2 et 100 caractères.")
        utilisateur.nom = nom
    # Note : le role n'est volontairement PAS modifiable ici (securite)

    db.commit()
    db.refresh(utilisateur)
    return utilisateur


# --- Statistiques d'activite de l'utilisateur connecte ---
@router.get("/moi/statistiques")
def mes_statistiques(
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Statistiques d'activite (12 derniers mois), bilan de securite et modele en service."""
    maintenant = datetime.utcnow()
    mes = db.query(models.Analyse).filter(models.Analyse.user_id == utilisateur.id,
                                          models.Analyse.date_analyse >= maintenant - timedelta(days=365))
    total = mes.count()
    accordes = mes.filter(models.Analyse.decision == "ACCORDE").count()
    refuses = mes.filter(models.Analyse.decision == "REFUSE").count()
    # Credits accordes depuis plus de 30 jours dont l'issue n'est pas encore renseignee
    issues = db.query(models.Analyse).filter(
        models.Analyse.user_id == utilisateur.id, models.Analyse.decision == "ACCORDE",
        models.Analyse.resultat_reel.is_(None),
        models.Analyse.date_analyse < maintenant - timedelta(days=30)).count()

    version = db.query(models.ModelVersion).filter(models.ModelVersion.en_production == True).first()  # noqa: E712
    modele = None
    if version:
        numero = db.query(models.ModelVersion).filter(models.ModelVersion.id <= version.id).count()
        etat = db.get(models.EtatSurveillance, "etat")
        modele = {
            "version": numero, "algorithme": version.algorithme,
            "mise_en_service": (version.date_creation + DECALAGE_TCHAD).strftime("%d/%m/%Y") if version.date_creation else None,
            "auc_reelle": version.auc_reelle, "etat": etat.valeur if etat else None,
        }
    changement = utilisateur.date_changement_mdp
    return {
        "analyses_realisees": total,
        "credits_accordes": accordes,
        "credits_refuses": refuses,
        "taux_accord": round(100 * accordes / total) if total else None,
        "issues_a_renseigner": issues,
        "membre_depuis": utilisateur.date_creation.strftime("%d/%m/%Y") if utilisateur.date_creation else None,
        "mot_de_passe_change_le": (changement + DECALAGE_TCHAD).strftime("%d/%m/%Y") if changement else None,
        "jours_depuis_changement": (maintenant - changement).days if changement else None,
        "modele": modele,
    }


# --- Changement de mot de passe securise (avec verification de l'ancien) ---
class ChangementMotDePasse(BaseModel):
    ancien_mot_de_passe: str
    nouveau_mot_de_passe: str


@router.put("/moi/mot-de-passe")
def changer_mot_de_passe(
    donnees: ChangementMotDePasse,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Change le mot de passe apres verification de l'ancien."""
    if not verifier_mot_de_passe(donnees.ancien_mot_de_passe, utilisateur.mot_de_passe):
        raise HTTPException(status_code=400, detail="L'ancien mot de passe est incorrect")
    if donnees.nouveau_mot_de_passe == donnees.ancien_mot_de_passe:
        raise HTTPException(status_code=400, detail="Le nouveau mot de passe doit être différent de l'ancien.")
    _verifier_regles(donnees.nouveau_mot_de_passe, utilisateur.nom, utilisateur.email)
    utilisateur.mot_de_passe = hacher_mot_de_passe(donnees.nouveau_mot_de_passe)
    utilisateur.date_changement_mdp = datetime.utcnow()
    db.commit()
    return {"message": "Mot de passe modifie avec succes"}


# --- Changement de son propre e-mail (administrateur, mot de passe exige) ---
class ChangementEmail(BaseModel):
    nouvel_email: EmailStr
    mot_de_passe: str


@router.put("/moi/email")
def changer_mon_email(
    donnees: ChangementEmail,
    db: Session = Depends(get_db),
    admin: models.User = Depends(administrateur_courant),
):
    """Un administrateur change son propre e-mail (son identifiant de connexion).

    Le mot de passe actuel est exige. Le jeton de connexion contient l'e-mail :
    un nouveau jeton est renvoye pour que la session continue."""
    if not verifier_mot_de_passe(donnees.mot_de_passe, admin.mot_de_passe):
        raise HTTPException(status_code=400, detail="Mot de passe incorrect.")
    email = donnees.nouvel_email.strip().lower()
    if email == admin.email.lower():
        raise HTTPException(status_code=400, detail="C'est déjà votre adresse e-mail.")
    if db.query(models.User).filter(func.lower(models.User.email) == email, models.User.id != admin.id).first():
        raise HTTPException(status_code=400, detail="Cet e-mail est déjà utilisé.")
    admin.email = email
    db.commit()
    return {"access_token": creer_jeton({"sub": admin.email, "role": admin.role}), "token_type": "bearer",
            "email": admin.email}


# ===========================================================================
# CRUD DES UTILISATEURS
# ===========================================================================

# --- CREATE : creer un utilisateur ---
@router.post("/utilisateurs", response_model=UtilisateurReponse, status_code=201)
def creer_utilisateur(
    donnees: UtilisateurCreation,
    db: Session = Depends(get_db),
    admin: models.User = Depends(administrateur_courant),
):
    """Cree un nouvel utilisateur. Reserve a l'administrateur.

    Verifie que l'e-mail est libre, hache le mot de passe, puis enregistre.
    Le premier administrateur est cree par app/creer_admin.py.
    """
    existant = db.query(models.User).filter(models.User.email == donnees.email).first()
    if existant:
        raise HTTPException(status_code=400, detail="Cet e-mail est deja utilise")

    if donnees.role not in ("agent", "admin"):
        raise HTTPException(status_code=400, detail="Role invalide (agent ou admin)")
    _verifier_regles(donnees.mot_de_passe, donnees.nom, donnees.email)

    utilisateur = models.User(
        nom=donnees.nom,
        email=donnees.email,
        mot_de_passe=hacher_mot_de_passe(donnees.mot_de_passe),
        role=donnees.role,
        date_changement_mdp=datetime.utcnow(),
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
        # Ne jamais retrograder le dernier administrateur (sinon plus personne
        # ne pourrait gerer les comptes)
        if utilisateur.role == "admin" and donnees.role != "admin":
            nb_admins = db.query(models.User).filter(models.User.role == "admin").count()
            if nb_admins <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="Impossible de retrograder le dernier administrateur",
                )
        utilisateur.role = donnees.role
    if donnees.mot_de_passe is not None:
        _verifier_regles(donnees.mot_de_passe, utilisateur.nom, utilisateur.email)
        utilisateur.mot_de_passe = hacher_mot_de_passe(donnees.mot_de_passe)
        utilisateur.date_changement_mdp = datetime.utcnow()

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
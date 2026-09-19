# -*- coding: utf-8 -*-
"""
Module de sécurité de l'API CREDISCORE.

Ce module regroupe toute la logique d'authentification :
- le hachage et la vérification des mots de passe (avec bcrypt),
- la création et la vérification des jetons d'accès (JWT),
- la récupération de l'utilisateur connecté à partir de son jeton.

Le mot de passe n'est jamais stocké en clair : seule son empreinte (hachée)
est enregistrée. La clé secrète servant à signer les jetons est lue depuis
le fichier .env et ne doit jamais être publiée.
"""

import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .database import get_db
from . import models

load_dotenv()

# --- Configuration ---
SECRET_KEY = os.getenv("SECRET_KEY", "cle_par_defaut_a_changer")
ALGORITHME = "HS256"                     # algorithme de signature des jetons
DUREE_JETON_MINUTES = 60 * 8             # le jeton reste valide 8 heures

# Contexte de hachage des mots de passe (bcrypt)
contexte_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Indique à FastAPI où récupérer le jeton (la route de connexion)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/connexion")


# ---------------------------------------------------------------------------
# Mots de passe
# ---------------------------------------------------------------------------
def hacher_mot_de_passe(mot_de_passe: str) -> str:
    """Transforme un mot de passe en clair en une empreinte hachée."""
    return contexte_pwd.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, empreinte: str) -> bool:
    """Vérifie qu'un mot de passe correspond à son empreinte hachée."""
    return contexte_pwd.verify(mot_de_passe, empreinte)


# ---------------------------------------------------------------------------
# Jetons JWT
# ---------------------------------------------------------------------------
def creer_jeton(donnees: dict) -> str:
    """Crée un jeton d'accès signé, contenant les données fournies.

    Le jeton inclut une date d'expiration : au-delà, il n'est plus valable.
    """
    a_encoder = donnees.copy()
    expiration = datetime.utcnow() + timedelta(minutes=DUREE_JETON_MINUTES)
    a_encoder.update({"exp": expiration})
    return jwt.encode(a_encoder, SECRET_KEY, algorithm=ALGORITHME)


# ---------------------------------------------------------------------------
# Récupération de l'utilisateur connecté
# ---------------------------------------------------------------------------
def utilisateur_courant(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """Récupère l'utilisateur à partir de son jeton.

    Cette fonction sera utilisée comme dépendance dans les routes protégées :
    elle décode le jeton, en extrait l'email, et renvoie l'utilisateur
    correspondant. Si le jeton est invalide ou expiré, elle refuse l'accès.
    """
    exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Jeton invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        charge = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHME])
        email = charge.get("sub")
        if email is None:
            raise exception
    except JWTError:
        raise exception

    utilisateur = db.query(models.User).filter(models.User.email == email).first()
    if utilisateur is None:
        raise exception
    return utilisateur


def administrateur_courant(
    utilisateur: models.User = Depends(utilisateur_courant),
) -> models.User:
    """Vérifie que l'utilisateur connecté est un administrateur.

    Utilisée pour protéger les routes réservées à l'administrateur.
    """
    if utilisateur.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé à l'administrateur",
        )
    return utilisateur
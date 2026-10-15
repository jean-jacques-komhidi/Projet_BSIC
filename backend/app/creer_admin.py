# -*- coding: utf-8 -*-
"""
Creation du premier administrateur CREDISCORE.

La route publique de creation de compte n'existe plus : seul un administrateur
peut creer des utilisateurs. Ce script cree le tout premier administrateur, a
partir de variables d'environnement (jamais ecrites dans le code) :

    ADMIN_EMAIL     adresse e-mail de l'administrateur
    ADMIN_PASSWORD  mot de passe (8 caracteres minimum)
    ADMIN_NOM       nom affiche (facultatif, "Administrateur" par defaut)

Il ne fait rien si un administrateur existe deja : on peut donc le lancer a
chaque demarrage sans risque. Si l'e-mail appartient deja a un agent, ce
compte est promu administrateur (son mot de passe n'est pas modifie).

Utilisation, depuis le dossier backend :
    python -m app.creer_admin
"""

import os

from .database import SessionLocal
from . import models
from .security import hacher_mot_de_passe


def creer_premier_admin():
    email = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
    mot_de_passe = os.getenv("ADMIN_PASSWORD") or ""
    nom = (os.getenv("ADMIN_NOM") or "Administrateur").strip()

    db = SessionLocal()
    try:
        if db.query(models.User).filter(models.User.role == "admin").first():
            print("Un administrateur existe deja : rien a faire.")
            return

        if not email or not mot_de_passe:
            print("Aucun administrateur, et ADMIN_EMAIL / ADMIN_PASSWORD absents : "
                  "aucun compte cree.")
            return
        if len(mot_de_passe) < 8:
            print("ADMIN_PASSWORD doit faire au moins 8 caracteres : aucun compte cree.")
            return

        existant = db.query(models.User).filter(models.User.email == email).first()
        if existant:
            existant.role = "admin"
            print(f"Compte existant {email} promu administrateur.")
        else:
            db.add(models.User(
                nom=nom,
                email=email,
                mot_de_passe=hacher_mot_de_passe(mot_de_passe),
                role="admin",
            ))
            print(f"Administrateur {email} cree.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    creer_premier_admin()

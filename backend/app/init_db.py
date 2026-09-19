# -*- coding: utf-8 -*-
"""
Initialisation de la base de données CREDISCORE.

Ce script crée toutes les tables dans la base PostgreSQL, à partir des
définitions du module models. À lancer une seule fois, après avoir créé la
base 'credit_bsic' dans PostgreSQL.

Utilisation, depuis le dossier backend :
    python -m app.init_db
"""

from .database import Base, engine
from . import models  # importe les tables pour qu'elles soient enregistrées


def creer_tables():
    """Crée toutes les tables définies dans models."""
    print("Création des tables dans la base de données...")
    Base.metadata.create_all(bind=engine)
    print("Tables créées avec succès :")
    for table in Base.metadata.tables:
        print("  -", table)


if __name__ == "__main__":
    creer_tables()
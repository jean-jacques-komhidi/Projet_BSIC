# -*- coding: utf-8 -*-
"""
Initialisation de la base de données CREDISCORE.

Ce script crée toutes les tables dans la base PostgreSQL, à partir des
définitions du module models. À lancer une seule fois, après avoir créé la
base 'credit_bsic' dans PostgreSQL.

Utilisation, depuis le dossier backend :
    python -m app.init_db
"""

from sqlalchemy import inspect, text

from .database import Base, engine
from . import models  # importe les tables pour qu'elles soient enregistrées

# Colonnes ajoutées après la création initiale des tables : create_all ne modifie
# pas une table existante, on les ajoute donc ici si elles manquent.
COLONNES_AJOUTEES = {
    "notifications": {
        "destinataire_id": "INTEGER REFERENCES users(id)",
        "categorie": "VARCHAR(20)",
        "lien": "VARCHAR(200)",
        "texte_lien": "VARCHAR(60)",
    },
    "model_versions": {
        "statut": "VARCHAR(20)",
        "auc_reelle": "FLOAT",
        "date_retrait": "TIMESTAMP",
    },
}


def mettre_a_jour_colonnes():
    """Ajoute les colonnes manquantes aux tables existantes (sans perte de données)."""
    inspecteur = inspect(engine)
    with engine.begin() as connexion:
        for table, colonnes in COLONNES_AJOUTEES.items():
            if not inspecteur.has_table(table):
                continue
            existantes = {c["name"] for c in inspecteur.get_columns(table)}
            for nom, type_sql in colonnes.items():
                if nom not in existantes:
                    if engine.dialect.name == "sqlite":
                        type_sql = type_sql.split(" REFERENCES")[0]
                    connexion.execute(text(f"ALTER TABLE {table} ADD COLUMN {nom} {type_sql}"))
                    print(f"  colonne ajoutée : {table}.{nom}")


def creer_tables():
    """Crée toutes les tables définies dans models, puis complète les anciennes."""
    print("Création des tables dans la base de données...")
    Base.metadata.create_all(bind=engine)
    mettre_a_jour_colonnes()
    print("Tables créées avec succès :")
    for table in Base.metadata.tables:
        print("  -", table)


if __name__ == "__main__":
    creer_tables()
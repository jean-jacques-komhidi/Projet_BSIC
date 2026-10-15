# -*- coding: utf-8 -*-
"""
Connexion à la base de données de l'API CREDISCORE.
Utilise psycopg (version 3).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "credit_bsic")

DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# En production (Render, Railway...), l'hebergeur fournit une seule variable
# DATABASE_URL au format postgres://... : on la convertit pour psycopg 3.
_url_hebergeur = os.getenv("DATABASE_URL")
if _url_hebergeur:
    for _prefixe in ("postgres://", "postgresql://"):
        if _url_hebergeur.startswith(_prefixe):
            _url_hebergeur = "postgresql+psycopg://" + _url_hebergeur[len(_prefixe):]
            break
    DATABASE_URL = _url_hebergeur

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ✅ Fonction utilitaire pour les dépendances FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

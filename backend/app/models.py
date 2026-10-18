# -*- coding: utf-8 -*-
"""
Tables de la base de donnees de l'API CREDISCORE.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    mot_de_passe = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="agent")
    date_creation = Column(DateTime, default=datetime.utcnow)
    analyses = relationship("Analyse", back_populates="utilisateur")


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(150), nullable=False)
    genre = Column(String(1))
    age = Column(Float)
    profession = Column(String(100))
    situation_familiale = Column(String(50))
    date_creation = Column(DateTime, default=datetime.utcnow)
    analyses = relationship("Analyse", back_populates="client")


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id = Column(Integer, primary_key=True, index=True)
    algorithme = Column(String(50), nullable=False)
    auc = Column(Float)
    en_production = Column(Boolean, default=False)
    date_creation = Column(DateTime, default=datetime.utcnow)
    # 'production', 'retire' ou 'rejete' (candidat moins bon que le modele en service)
    statut = Column(String(20), nullable=True)
    # AUC mesuree sur les issues reelles recentes lors du dernier reentrainement
    auc_reelle = Column(Float, nullable=True)
    date_retrait = Column(DateTime, nullable=True)
    # Debut de la periode de reference de la surveillance pour ce modele : apres une
    # mise en service, la derive est mesuree par rapport aux donnees recentes qu'il a apprises
    debut_reference = Column(DateTime, nullable=True)
    # Mesure de l'AUC reelle : nombre d'issues mises de cote, date, et AUC du modele
    # precedent sur ces memes issues (seules des mesures faites ensemble se comparent)
    nb_issues_validation = Column(Integer, nullable=True)
    date_mesure = Column(DateTime, nullable=True)
    auc_precedent = Column(Float, nullable=True)
    analyses = relationship("Analyse", back_populates="version_modele")


class Analyse(Base):
    __tablename__ = "analyses"
    id = Column(Integer, primary_key=True, index=True)
    probabilite_defaut = Column(Float, nullable=False)
    classe_risque = Column(String(20))
    decision = Column(String(20))
    facteurs_explicatifs = Column(Text)
    explication = Column(Text)                 # explication en langage naturel
    donnees_dossier = Column(Text)             # donnees d'entree du dossier (JSON)
    # Resultat reel constate a posteriori : 'rembourse', 'defaut' ou NULL (inconnu).
    # Seules les analyses au resultat connu servent au reentrainement.
    resultat_reel = Column(String(20), nullable=True)
    date_analyse = Column(DateTime, default=datetime.utcnow)

    client_id = Column(Integer, ForeignKey("clients.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    model_version_id = Column(Integer, ForeignKey("model_versions.id"))

    client = relationship("Client", back_populates="analyses")
    utilisateur = relationship("User", back_populates="analyses")
    version_modele = relationship("ModelVersion", back_populates="analyses")

class Notification(Base):
    """Une notification pour informer les utilisateurs d'un evenement."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    titre = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(30), default="info")   # info, succes, alerte, danger
    lue = Column(Boolean, default=False)
    date_creation = Column(DateTime, default=datetime.utcnow)
    # Destinataire : chaque personne a ses propres notifications (et son statut lu).
    # Les anciennes notifications sans destinataire sont reservees aux administrateurs.
    destinataire_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    categorie = Column(String(20), nullable=True)   # modele, dossiers
    lien = Column(String(200), nullable=True)       # page a ouvrir, ex. /monitoring
    texte_lien = Column(String(60), nullable=True)  # ex. "Ouvrir le monitoring"


class ExportDonnees(Base):
    """Journal des exports : qui a exporte quoi, pour qui et pourquoi (trace d'audit)."""
    __tablename__ = "exports_donnees"
    id = Column(Integer, primary_key=True, index=True)
    date_export = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    auteur = Column(String(100))
    jeu = Column(String(20))                 # analyses, clients, versions
    groupes = Column(String(200))            # groupes de colonnes exportes
    destinataire = Column(String(60))
    motif = Column(String(300))
    anonymise = Column(Boolean, default=True)
    format = Column(String(10))              # csv, xlsx
    periode_debut = Column(DateTime, nullable=True)
    periode_fin = Column(DateTime, nullable=True)
    nb_lignes = Column(Integer)


class EtatSurveillance(Base):
    """Memoire de la surveillance automatique (dernier etat, derniers rappels)."""
    __tablename__ = "etat_surveillance"

    cle = Column(String(50), primary_key=True)
    valeur = Column(String(200), nullable=True)
    date_maj = Column(DateTime, default=datetime.utcnow)


class Conversation(Base):
    """Une conversation avec l'assistant conversationnel."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    titre = Column(String(200), default="Nouvelle conversation")
    user_id = Column(Integer, ForeignKey("users.id"))
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_maj = Column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="conversation",
                            cascade="all, delete-orphan", order_by="Message.date_creation")


class Message(Base):
    """Un message dans une conversation (question de l'agent ou reponse de l'assistant)."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(20), nullable=False)   # 'user' ou 'assistant'
    contenu = Column(Text, nullable=False)
    date_creation = Column(DateTime, default=datetime.utcnow)

    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    conversation = relationship("Conversation", back_populates="messages")
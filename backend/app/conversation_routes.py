# -*- coding: utf-8 -*-
"""
Routes de gestion des conversations avec l'assistant.

  - GET    /conversations              : lister les conversations de l'utilisateur
  - POST   /conversations              : creer une nouvelle conversation
  - GET    /conversations/{id}         : lire une conversation (avec ses messages)
  - POST   /conversations/{id}/message : envoyer un message et obtenir la reponse
  - DELETE /conversations/{id}         : supprimer une conversation

Chaque conversation appartient a l'utilisateur qui l'a creee. L'assistant
garde le contexte de la conversation (les messages precedents) pour repondre.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .security import utilisateur_courant
from .chatbot_service import repondre

router = APIRouter(prefix="/conversations", tags=["Assistant - Conversations"])


# --- Schemas ---
class MessageReponse(BaseModel):
    id: int
    role: str
    contenu: str
    date_creation: datetime
    class Config:
        from_attributes = True

class ConversationResume(BaseModel):
    id: int
    titre: str
    date_maj: datetime
    class Config:
        from_attributes = True

class ConversationDetail(BaseModel):
    id: int
    titre: str
    messages: list[MessageReponse]
    class Config:
        from_attributes = True

class QuestionEnvoi(BaseModel):
    question: str = Field(..., description="La question de l'agent")
    analyse_id: Optional[int] = Field(None, description="Optionnel : id d'une analyse")


# --- CREATE : nouvelle conversation ---
@router.post("", response_model=ConversationResume, status_code=201)
def creer_conversation(
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Cree une nouvelle conversation vide."""
    conv = models.Conversation(titre="Nouvelle conversation", user_id=utilisateur.id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


# --- READ : lister les conversations de l'utilisateur ---
@router.get("", response_model=list[ConversationResume])
def lister_conversations(
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Liste les conversations de l'utilisateur, les plus recentes d'abord."""
    return db.query(models.Conversation).filter(
        models.Conversation.user_id == utilisateur.id
    ).order_by(models.Conversation.date_maj.desc()).all()


# --- READ : lire une conversation avec ses messages ---
@router.get("/{conv_id}", response_model=ConversationDetail)
def lire_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Renvoie une conversation et tous ses messages."""
    conv = db.query(models.Conversation).filter(
        models.Conversation.id == conv_id,
        models.Conversation.user_id == utilisateur.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return conv


# --- POST : envoyer un message et obtenir la reponse ---
@router.post("/{conv_id}/message")
def envoyer_message(
    conv_id: int,
    envoi: QuestionEnvoi,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Enregistre la question, obtient la reponse de l'assistant (avec contexte
    de la conversation), l'enregistre, et renvoie les deux messages."""
    conv = db.query(models.Conversation).filter(
        models.Conversation.id == conv_id,
        models.Conversation.user_id == utilisateur.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    # Recuperer l'historique des messages precedents (pour le contexte)
    historique = [
        {"role": m.role, "contenu": m.contenu}
        for m in conv.messages
    ]

    # Enregistrer la question de l'utilisateur
    msg_user = models.Message(role="user", contenu=envoi.question, conversation_id=conv.id)
    db.add(msg_user)

    # Si c'est le premier message, definir le titre de la conversation
    if len(conv.messages) == 0:
        conv.titre = envoi.question[:60] + ("..." if len(envoi.question) > 60 else "")

    # Obtenir la reponse de l'assistant avec le contexte de la conversation
    texte_reponse = repondre(db, envoi.question, envoi.analyse_id, historique=historique)

    # Enregistrer la reponse
    msg_assistant = models.Message(role="assistant", contenu=texte_reponse, conversation_id=conv.id)
    db.add(msg_assistant)

    conv.date_maj = datetime.utcnow()
    db.commit()
    db.refresh(msg_user)
    db.refresh(msg_assistant)

    return {
        "question": {"role": "user", "contenu": envoi.question},
        "reponse": {"role": "assistant", "contenu": texte_reponse},
    }


# --- DELETE : supprimer une conversation ---
@router.delete("/{conv_id}")
def supprimer_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Supprime une conversation et tous ses messages."""
    conv = db.query(models.Conversation).filter(
        models.Conversation.id == conv_id,
        models.Conversation.user_id == utilisateur.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    db.delete(conv)
    db.commit()
    return {"message": "Conversation supprimee", "id": conv_id}
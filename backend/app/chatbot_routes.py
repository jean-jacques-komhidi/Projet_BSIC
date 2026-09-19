# -*- coding: utf-8 -*-
"""
Route de l'assistant conversationnel (chatbot).

  - POST /chatbot : poser une question a l'assistant

L'agent envoie une question en langage naturel. S'il precise un identifiant
d'analyse, la question porte sur ce dossier ; sinon, elle porte sur les
donnees generales. Necessite d'etre connecte.
"""

from pydantic import BaseModel, Field
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .security import utilisateur_courant
from .chatbot_service import repondre

router = APIRouter(prefix="/chatbot", tags=["Assistant"])


class Question(BaseModel):
    """Question posee a l'assistant."""
    question: str = Field(..., description="La question en langage naturel")
    analyse_id: Optional[int] = Field(
        None, description="Optionnel : id d'une analyse pour une question sur un dossier precis")


class Reponse(BaseModel):
    """Reponse de l'assistant."""
    reponse: str


@router.post("", response_model=Reponse)
def poser_question(
    q: Question,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Pose une question a l'assistant conversationnel."""
    texte = repondre(db, q.question, q.analyse_id)
    return {"reponse": texte}
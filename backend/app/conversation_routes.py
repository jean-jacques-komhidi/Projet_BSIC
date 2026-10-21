# -*- coding: utf-8 -*-
"""
Routes de gestion des conversations avec l'assistant.

  - GET    /conversations              : lister les conversations de l'utilisateur
  - POST   /conversations              : creer une nouvelle conversation
  - GET    /conversations/{id}         : lire une conversation (avec ses messages)
  - POST   /conversations/{id}/message : envoyer un message et obtenir la reponse
  - POST   /conversations/{id}/message/flux : idem, mais la reponse arrive
                                         progressivement (streaming)
  - DELETE /conversations/{id}         : supprimer une conversation

Chaque conversation appartient a l'utilisateur qui l'a creee. L'assistant
garde le contexte de la conversation (les messages precedents) pour repondre.
"""

import re
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .database import get_db, SessionLocal
from . import models
from .security import utilisateur_courant
from .chatbot_service import repondre, preparer_requete, repondre_en_flux

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
    apercu: Optional[str] = None
    class Config:
        from_attributes = True

class DossierJoint(BaseModel):
    id: int
    reference: str
    client: Optional[str] = None

class ConversationDetail(BaseModel):
    id: int
    titre: str
    messages: list[MessageReponse]
    dossier: Optional[DossierJoint] = None
    class Config:
        from_attributes = True


LONGUEUR_APERCU = 90


def _apercu(conv) -> Optional[str]:
    """Debut de la derniere reponse de CrediBot, sans la mise en forme Markdown."""
    reponses = [m for m in conv.messages if m.role == "assistant" and m.contenu]
    if not reponses:
        return None
    texte = re.sub(r"\[PDF:\d+\]", "", reponses[-1].contenu)
    texte = re.sub(r"[*_#`>|]+", "", texte)
    texte = " ".join(texte.split())
    return texte[:LONGUEUR_APERCU] + ("…" if len(texte) > LONGUEUR_APERCU else "")


def _dossier(db: Session, analyse_id) -> Optional[dict]:
    """Reference et client du dossier joint, ou None s'il n'existe pas (ou plus)."""
    if not analyse_id:
        return None
    a = db.query(models.Analyse).filter(models.Analyse.id == analyse_id).first()
    if not a:
        return None
    client = db.query(models.Client).filter(models.Client.id == a.client_id).first()
    annee = a.date_analyse.year if a.date_analyse else 0
    return {"id": a.id, "reference": f"CRED-{annee}-{a.id:04d}", "client": client.nom if client else None}


def _joindre(db: Session, conv, analyse_id) -> Optional[int]:
    """Memorise le dossier joint au message (None = aucun) et renvoie son id s'il existe."""
    if analyse_id is not None and not db.query(models.Analyse.id).filter(models.Analyse.id == analyse_id).first():
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    conv.analyse_id = analyse_id
    return analyse_id

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
    """Liste les conversations de l'utilisateur, les plus recentes d'abord,
    avec un apercu de la derniere reponse."""
    convs = db.query(models.Conversation).filter(
        models.Conversation.user_id == utilisateur.id
    ).order_by(models.Conversation.date_maj.desc()).all()
    return [{"id": c.id, "titre": c.titre, "date_maj": c.date_maj, "apercu": _apercu(c)} for c in convs]


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
    return {"id": conv.id, "titre": conv.titre, "messages": conv.messages,
            "dossier": _dossier(db, conv.analyse_id)}


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

    # Recuperer l'historique des messages precedents (pour le contexte).
    # On ne garde que les 10 derniers pour limiter la taille du prompt ; cet
    # historique est fige AVANT d'ajouter la question courante, pour ne pas la
    # transmettre deux fois au modele de langage.
    historique = [
        {"role": m.role, "contenu": m.contenu}
        for m in conv.messages[-10:]
    ]
    premier_message = len(conv.messages) == 0

    _joindre(db, conv, envoi.analyse_id)

    # Enregistrer la question de l'utilisateur
    msg_user = models.Message(role="user", contenu=envoi.question, conversation_id=conv.id)
    db.add(msg_user)

    # Si c'est le premier message, definir le titre de la conversation
    if premier_message:
        conv.titre = envoi.question[:60] + ("..." if len(envoi.question) > 60 else "")

    # Obtenir la reponse de l'assistant avec le contexte de la conversation
    texte_reponse = repondre(db, envoi.question, envoi.analyse_id,
                             historique=historique, utilisateur=utilisateur)

    # Enregistrer la reponse
    msg_assistant = models.Message(role="assistant", contenu=texte_reponse, conversation_id=conv.id)
    db.add(msg_assistant)

    conv.date_maj = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg_user)
    db.refresh(msg_assistant)

    return {
        "question": {"role": "user", "contenu": envoi.question},
        "reponse": {"role": "assistant", "contenu": texte_reponse},
    }


# --- POST : envoyer un message, reponse progressive (streaming) ---
@router.post("/{conv_id}/message/flux")
def envoyer_message_flux(
    conv_id: int,
    envoi: QuestionEnvoi,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Comme /message, mais la reponse est envoyee au fur et a mesure qu'elle
    est generee (texte brut, morceau par morceau), comme dans ChatGPT.
    La reponse complete est enregistree a la fin du flux."""
    conv = db.query(models.Conversation).filter(
        models.Conversation.id == conv_id,
        models.Conversation.user_id == utilisateur.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    historique = [{"role": m.role, "contenu": m.contenu} for m in conv.messages[-10:]]
    premier_message = len(conv.messages) == 0

    _joindre(db, conv, envoi.analyse_id)

    # La question est enregistree tout de suite
    db.add(models.Message(role="user", contenu=envoi.question, conversation_id=conv.id))
    if premier_message:
        conv.titre = envoi.question[:60] + ("..." if len(envoi.question) > 60 else "")
    conv.date_maj = datetime.now(timezone.utc)
    db.commit()

    # Le contexte est prepare AVANT le flux, avec la session de la requete
    liste_messages, ps, erreur = preparer_requete(
        db, envoi.question, envoi.analyse_id, historique=historique, utilisateur=utilisateur)

    def generer():
        morceaux = []
        if erreur:
            morceaux.append(erreur)
            yield erreur
        else:
            for morceau in repondre_en_flux(liste_messages, ps):
                morceaux.append(morceau)
                yield morceau
        # Fin du flux : on enregistre la reponse complete. Session dediee, car
        # celle de la requete peut deja etre fermee pendant le streaming.
        session = SessionLocal()
        try:
            session.add(models.Message(role="assistant", contenu="".join(morceaux).strip(),
                                       conversation_id=conv_id))
            c = session.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
            if c:
                c.date_maj = datetime.now(timezone.utc)
            session.commit()
        finally:
            session.close()

    return StreamingResponse(
        generer(),
        media_type="text/plain; charset=utf-8",
        # Empeche les proxys (Render, Nginx) de retenir le flux jusqu'a la fin
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
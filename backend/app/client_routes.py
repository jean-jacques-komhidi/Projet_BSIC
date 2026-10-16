# -*- coding: utf-8 -*-
"""
Routes de gestion des clients (CRUD complet + recherche).

  - POST   /clients             : creer un client (Create)
  - GET    /clients             : lister les clients (Read)
  - GET    /clients/recherche   : rechercher des clients par nom (Read)
  - GET    /clients/synthese    : clients avec le resume de leurs analyses (Read)
  - GET    /clients/{id}        : voir un client (Read)
  - PUT    /clients/{id}        : modifier un client (Update)
  - DELETE /clients/{id}        : supprimer un client sans analyse (Delete, admin)

Toutes ces routes necessitent d'etre connecte (agent ou administrateur).
La suppression est reservee a l'administrateur.
"""

import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .schemas_client import ClientCreation, ClientModification, ClientReponse
from .security import utilisateur_courant, administrateur_courant

router = APIRouter(prefix="/clients", tags=["Clients"])


# --- CREATE : creer un client ---
@router.post("", response_model=ClientReponse, status_code=201)
def creer_client(
    donnees: ClientCreation,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Cree un nouveau client. Necessite d'etre connecte."""
    client = models.Client(
        nom=donnees.nom,
        genre=donnees.genre,
        age=donnees.age,
        profession=donnees.profession,
        situation_familiale=donnees.situation_familiale,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


# --- READ : lister les clients ---
@router.get("", response_model=list[ClientReponse])
def lister_clients(
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Liste tous les clients. Necessite d'etre connecte."""
    return db.query(models.Client).all()


# --- READ : rechercher des clients par nom ---
# IMPORTANT : cette route doit etre declaree AVANT /clients/{client_id},
# sinon "recherche" serait interprete comme un identifiant.
@router.get("/recherche", response_model=list[ClientReponse])
def rechercher_clients(
    nom: str = Query(..., min_length=1, description="Nom (ou partie du nom) a rechercher"),
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Recherche les clients dont le nom contient le texte fourni.

    La recherche est partielle et insensible a la casse : chercher "kad"
    trouvera "Kadidja Moussa". Necessite d'etre connecte.
    """
    motif = f"%{nom}%"
    clients = db.query(models.Client).filter(
        models.Client.nom.ilike(motif)
    ).all()
    return clients


# --- READ : synthese des clients (liste enrichie) ---
SEUIL_REFUS = 0.70
JOURS_ACTIVITE = 90


def _montant(analyse):
    try:
        return float(json.loads(analyse.donnees_dossier or "{}").get("AMT_CREDIT") or 0)
    except (TypeError, ValueError):
        return 0.0


def _resume(client, analyses, maintenant):
    """Resume d'un client a partir de ses analyses (de la plus ancienne a la plus recente)."""
    probas = [a.probabilite_defaut or 0 for a in analyses]
    derniere = analyses[-1] if analyses else None
    accordes = [a for a in analyses if a.decision == "ACCORDE"]
    defauts = sum(1 for a in accordes if a.resultat_reel == "defaut")
    issues = [a.resultat_reel for a in accordes if a.resultat_reel]
    hausse = len(probas) >= 3 and probas[-1] - probas[-2] >= 0.03 and probas[-2] - probas[-3] >= 0.03
    motifs = []
    if derniere and derniere.decision == "REFUSE":
        motifs.append("Dernière demande refusée")
    if hausse:
        motifs.append("Risque en hausse continue")
    if issues and issues[-1] == "defaut":
        motifs.append("Dernier crédit connu en défaut")
    return {
        "id": client.id, "nom": client.nom, "genre": client.genre, "age": client.age,
        "profession": client.profession, "situation_familiale": client.situation_familiale,
        "date_creation": client.date_creation,
        "nb_analyses": len(analyses),
        "probabilites": [round(p, 4) for p in probas[-8:]],
        "tendance": round((probas[-1] - probas[-2]) * 100) if len(probas) >= 2 else None,
        "derniere_analyse": {
            "id": derniere.id, "date": derniere.date_analyse,
            "probabilite_defaut": derniere.probabilite_defaut,
            "classe_risque": derniere.classe_risque, "decision": derniere.decision,
            "montant": _montant(derniere),
        } if derniere else None,
        "actif": bool(derniere and derniere.date_analyse
                      and maintenant - derniere.date_analyse <= timedelta(days=JOURS_ACTIVITE)),
        "credits": {
            "accordes": len(accordes),
            "rembourses": sum(1 for a in accordes if a.resultat_reel == "rembourse"),
            "defauts": defauts,
            "en_cours": sum(1 for a in accordes if not a.resultat_reel),
            "montant_accorde": sum(_montant(a) for a in accordes),
        },
        "a_surveiller": bool(motifs),
        "motifs": motifs,
    }


@router.get("/synthese")
def synthese_clients(
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Liste des clients avec le resume de leurs analyses : nombre, derniere
    analyse, evolution du risque, credits et motifs de vigilance."""
    par_client = {}
    for a in db.query(models.Analyse).order_by(models.Analyse.date_analyse.asc()).all():
        par_client.setdefault(a.client_id, []).append(a)
    maintenant = datetime.utcnow()
    return [_resume(c, par_client.get(c.id, []), maintenant)
            for c in db.query(models.Client).order_by(models.Client.nom).all()]


# --- READ : voir un client precis ---
@router.get("/{client_id}", response_model=ClientReponse)
def voir_client(
    client_id: int,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Renvoie un client precis. Necessite d'etre connecte."""
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")
    return client


# --- UPDATE : modifier un client ---
@router.put("/{client_id}", response_model=ClientReponse)
def modifier_client(
    client_id: int,
    donnees: ClientModification,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Modifie un client. Seuls les champs fournis sont modifies."""
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")

    donnees_fournies = donnees.model_dump(exclude_unset=True)
    for champ, valeur in donnees_fournies.items():
        setattr(client, champ, valeur)

    db.commit()
    db.refresh(client)
    return client


# --- DELETE : supprimer un client ---
@router.delete("/{client_id}", status_code=200)
def supprimer_client(
    client_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(administrateur_courant),
):
    """Supprime un client. Reserve a l'administrateur.

    Un client qui a des analyses n'est pas supprime : ses decisions de credit
    doivent rester tracables. Il faut d'abord supprimer ses analyses."""
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")
    nb = db.query(models.Analyse).filter(models.Analyse.client_id == client_id).count()
    if nb:
        raise HTTPException(
            status_code=409,
            detail=f"Ce client a {nb} analyse{'s' if nb > 1 else ''} : supprimez-les d'abord "
                   "depuis l'historique (les décisions de crédit doivent rester traçables).")

    db.delete(client)
    db.commit()
    return {"message": "Client supprime", "id": client_id}
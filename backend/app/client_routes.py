# -*- coding: utf-8 -*-
"""
Routes de gestion des clients (CRUD complet + recherche).

  - POST   /clients             : creer un client (Create)
  - GET    /clients             : lister les clients (Read)
  - GET    /clients/recherche   : rechercher des clients par nom (Read)
  - GET    /clients/{id}        : voir un client (Read)
  - PUT    /clients/{id}        : modifier un client (Update)
  - DELETE /clients/{id}        : supprimer un client (Delete)

Toutes ces routes necessitent d'etre connecte (agent ou administrateur).
La suppression est reservee a l'administrateur.
"""

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
    """Supprime un client. Reserve a l'administrateur."""
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")

    db.delete(client)
    db.commit()
    return {"message": "Client supprime", "id": client_id}
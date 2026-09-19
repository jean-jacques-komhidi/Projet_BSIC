# -*- coding: utf-8 -*-
"""
Routes de gestion des analyses de credit enregistrees.

  - POST /analyses                  : realiser et enregistrer une analyse
  - GET  /analyses                  : lister toutes les analyses
  - GET  /analyses/{id}             : voir une analyse precise
  - GET  /analyses/client/{id}      : lister les analyses d'un client
  - PUT  /analyses/{id}/resultat    : renseigner le resultat reel (admin)

Chaque analyse enregistre le score, la decision, l'explication, ET les donnees
du dossier (pour un eventuel reentrainement). Le resultat reel (rembourse /
defaut) est renseigne a posteriori, une fois l'issue du credit connue.
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .schemas_analyse import AnalyseCreation, AnalyseReponse
from .security import utilisateur_courant, administrateur_courant
from .model_service import ServiceModele

router = APIRouter(prefix="/analyses", tags=["Analyses"])

service = ServiceModele()


def obtenir_version_modele(db: Session) -> models.ModelVersion:
    """Recupere la version du modele en production, ou la cree si absente."""
    version = db.query(models.ModelVersion).filter(
        models.ModelVersion.en_production == True
    ).first()
    if not version:
        version = models.ModelVersion(
            algorithme="Gradient Boosting", auc=0.753, en_production=True)
        db.add(version)
        db.commit()
        db.refresh(version)
    return version


# --- CREATE : realiser et enregistrer une analyse ---
@router.post("", response_model=AnalyseReponse, status_code=201)
def realiser_analyse(
    donnees: AnalyseCreation,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Realise une analyse de credit et l'enregistre."""
    client = db.query(models.Client).filter(
        models.Client.id == donnees.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")

    dossier = donnees.dossier.model_dump()
    resultat = service.analyser(dossier)
    version = obtenir_version_modele(db)

    analyse = models.Analyse(
        probabilite_defaut=resultat["probabilite_defaut"],
        classe_risque=resultat["classe_risque"],
        decision=resultat["decision"],
        facteurs_explicatifs=json.dumps(resultat["facteurs_explicatifs"], ensure_ascii=False),
        explication=resultat.get("explication", ""),
        donnees_dossier=json.dumps(dossier, ensure_ascii=False),
        client_id=client.id,
        user_id=utilisateur.id,
        model_version_id=version.id,
    )
    db.add(analyse)
    db.commit()
    db.refresh(analyse)
    return analyse


# --- READ : lister toutes les analyses ---
@router.get("", response_model=list[AnalyseReponse])
def lister_analyses(
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    return db.query(models.Analyse).order_by(models.Analyse.date_analyse.desc()).all()


# --- READ : voir une analyse precise ---
@router.get("/{analyse_id}", response_model=AnalyseReponse)
def voir_analyse(
    analyse_id: int,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    analyse = db.query(models.Analyse).filter(models.Analyse.id == analyse_id).first()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return analyse


# --- READ : lister les analyses d'un client ---
@router.get("/client/{client_id}", response_model=list[AnalyseReponse])
def analyses_du_client(
    client_id: int,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    return db.query(models.Analyse).filter(
        models.Analyse.client_id == client_id
    ).order_by(models.Analyse.date_analyse.desc()).all()


# --- UPDATE : renseigner le resultat reel (pour le reentrainement) ---
@router.put("/{analyse_id}/resultat", response_model=AnalyseReponse)
def renseigner_resultat(
    analyse_id: int,
    resultat: str,
    db: Session = Depends(get_db),
    admin: models.User = Depends(administrateur_courant),
):
    """Renseigne le resultat reel d'une analyse (rembourse ou defaut).

    A utiliser une fois l'issue du credit connue. Reserve a l'administrateur.
    Ce resultat permettra d'utiliser l'analyse lors du reentrainement.
    """
    if resultat not in ("rembourse", "defaut"):
        raise HTTPException(status_code=400,
                            detail="Resultat invalide : 'rembourse' ou 'defaut'")
    analyse = db.query(models.Analyse).filter(models.Analyse.id == analyse_id).first()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    analyse.resultat_reel = resultat
    db.commit()
    db.refresh(analyse)
    return analyse


# --- EXPORT PDF : telecharger la fiche de decision ---
from fastapi.responses import Response
from .pdf_service import generer_pdf_decision


@router.get("/{analyse_id}/pdf")
def exporter_pdf(
    analyse_id: int,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Genere et telecharge la fiche de decision d'une analyse au format PDF."""
    analyse = db.query(models.Analyse).filter(models.Analyse.id == analyse_id).first()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    client = db.query(models.Client).filter(models.Client.id == analyse.client_id).first()
    agent = db.query(models.User).filter(models.User.id == analyse.user_id).first()
    agent_nom = agent.nom if agent else "-"

    pdf = generer_pdf_decision(analyse, client, agent_nom)
    nom_fichier = f"fiche_decision_analyse_{analyse_id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nom_fichier}"},
    )
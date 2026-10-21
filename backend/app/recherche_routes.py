# -*- coding: utf-8 -*-
"""
Recherche globale de la barre du haut (Ctrl K).

  - GET /recherche?q=...   : clients et analyses correspondant au texte

On cherche les clients par nom, et les analyses par reference (CRED-2026-0121,
ou simplement 121) ou par nom du client. Cinq resultats au plus par categorie.
Necessite d'etre connecte : la recherche ne donne acces qu'aux donnees deja
visibles dans l'historique et la liste des clients.
"""

import json
import re
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .security import utilisateur_courant

router = APIRouter(prefix="/recherche", tags=["Recherche"])

LIMITE = 5
DECALAGE_TCHAD = timedelta(hours=1)


def _date(d):
    return (d + DECALAGE_TCHAD).strftime("%d/%m/%Y") if d else None


def _reference(a):
    return f"CRED-{a.date_analyse.year if a.date_analyse else 0}-{a.id:04d}"


def _montant(a):
    try:
        return json.loads(a.donnees_dossier or "{}").get("AMT_CREDIT")
    except (TypeError, ValueError):
        return None


def _risque_en_hausse(analyses):
    """Vrai si le risque monte depuis les trois dernieres analyses (comme l'alerte agent)."""
    if len(analyses) < 3:
        return False
    p = [a.probabilite_defaut for a in reversed(analyses[:3])]
    return p[1] - p[0] >= 0.03 and p[2] - p[1] >= 0.03


@router.get("")
def rechercher(
    q: str = Query(..., min_length=2, max_length=60),
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    texte = q.strip()
    motif = f"%{texte}%"

    # --- Clients ---
    clients = db.query(models.Client).filter(models.Client.nom.ilike(motif)) \
        .order_by(models.Client.nom).limit(LIMITE).all()
    resultats_clients = []
    for c in clients:
        analyses = db.query(models.Analyse).filter(models.Analyse.client_id == c.id) \
            .order_by(models.Analyse.date_analyse.desc()).all()
        resultats_clients.append({
            "id": c.id, "nom": c.nom, "nb_analyses": len(analyses),
            "derniere_analyse": _date(analyses[0].date_analyse) if analyses else None,
            "derniere_analyse_id": analyses[0].id if analyses else None,
            "risque_en_hausse": _risque_en_hausse(analyses),
        })

    # --- Analyses : par reference, sinon par nom du client ---
    requete = db.query(models.Analyse, models.Client).outerjoin(models.Client, models.Analyse.client_id == models.Client.id)
    numero = re.fullmatch(r"(?:cred-?\d{4}-?)?0*(\d{1,7})", texte.lower().replace(" ", ""))
    if numero:
        requete = requete.filter(models.Analyse.id == int(numero.group(1)))
    else:
        requete = requete.filter(models.Client.nom.ilike(motif))
    lignes = requete.order_by(models.Analyse.date_analyse.desc()).limit(LIMITE).all()
    resultats_analyses = [{
        "id": a.id, "reference": _reference(a), "client": c.nom if c else None,
        "date": _date(a.date_analyse), "montant": _montant(a),
        "probabilite_defaut": a.probabilite_defaut, "decision": a.decision,
    } for a, c in lignes]

    return {"clients": resultats_clients, "analyses": resultats_analyses}

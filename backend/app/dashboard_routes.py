# -*- coding: utf-8 -*-
"""
Route du tableau de bord (statistiques).

  - GET /dashboard : renvoie les statistiques agregees (agent ou admin)

Fournit une vue d'ensemble : nombre de clients et
d'analyses, taux d'acceptation, repartition des risques, activite recente.
Ces donnees seront affichees sous forme de graphiques dans l'interface.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from .database import get_db
from . import models
from .security import utilisateur_courant

router = APIRouter(prefix="/dashboard", tags=["Tableau de bord"])


@router.get("")
def tableau_de_bord(
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Renvoie les statistiques agregees. Accessible a tout utilisateur connecte."""

    total_clients = db.query(models.Client).count()
    total_analyses = db.query(models.Analyse).count()
    total_utilisateurs = db.query(models.User).count()

    accordes = db.query(models.Analyse).filter(
        models.Analyse.decision == "ACCORDE").count()
    refuses = db.query(models.Analyse).filter(
        models.Analyse.decision == "REFUSE").count()

    # Taux d'acceptation
    taux_acceptation = round(100 * accordes / total_analyses, 1) if total_analyses else 0

    # Repartition par classe de risque
    risque = {
        "faible": db.query(models.Analyse).filter(models.Analyse.classe_risque == "faible").count(),
        "moyen": db.query(models.Analyse).filter(models.Analyse.classe_risque == "moyen").count(),
        "eleve": db.query(models.Analyse).filter(models.Analyse.classe_risque == "eleve").count(),
    }

    # Probabilite moyenne de defaut
    proba_moy = db.query(func.avg(models.Analyse.probabilite_defaut)).scalar()
    proba_moyenne = round(proba_moy * 100, 1) if proba_moy else 0

    # Nombre d'analyses avec resultat reel connu (utiles au reentrainement)
    resultats_connus = db.query(models.Analyse).filter(
        models.Analyse.resultat_reel.in_(["rembourse", "defaut"])).count()

    # Version du modele en production
    version = db.query(models.ModelVersion).filter(
        models.ModelVersion.en_production == True).first()
    modele_production = {
        "algorithme": version.algorithme if version else None,
        "auc": version.auc if version else None,
    }

    # Les 5 dernieres analyses (activite recente)
    recentes = db.query(models.Analyse).order_by(
        models.Analyse.date_analyse.desc()).limit(5).all()
    activite_recente = []
    for a in recentes:
        client = db.query(models.Client).filter(models.Client.id == a.client_id).first()
        # Recuperer le revenu depuis les donnees du dossier (stockees en JSON)
        revenu = None
        if a.donnees_dossier:
            import json as _json
            try:
                revenu = _json.loads(a.donnees_dossier).get("AMT_INCOME_TOTAL")
            except Exception:
                revenu = None
        activite_recente.append({
            "id": a.id,
            "nom_client": client.nom if client else "-",
            "revenu": revenu,
            "decision": a.decision,
            "classe_risque": a.classe_risque,
            "probabilite_defaut": round(a.probabilite_defaut * 100, 1),
            "date": a.date_analyse.strftime("%d/%m/%Y %H:%M") if a.date_analyse else None,
        })

    # Evolution sur les 7 derniers jours : nombre d'analyses par jour
    evolution = []
    aujourd_hui = datetime.utcnow().date()
    for i in range(6, -1, -1):
        jour = aujourd_hui - timedelta(days=i)
        debut = datetime(jour.year, jour.month, jour.day)
        fin = debut + timedelta(days=1)
        nb = db.query(models.Analyse).filter(
            models.Analyse.date_analyse >= debut,
            models.Analyse.date_analyse < fin,
        ).count()
        # Taux de defaut moyen du jour
        proba_jour = db.query(func.avg(models.Analyse.probabilite_defaut)).filter(
            models.Analyse.date_analyse >= debut,
            models.Analyse.date_analyse < fin,
        ).scalar()
        evolution.append({
            "jour": jour.strftime("%d/%m"),
            "analyses": nb,
            "risque_moyen": round(proba_jour * 100, 1) if proba_jour else 0,
        })

    return {
        "totaux": {
            "clients": total_clients,
            "analyses": total_analyses,
            "utilisateurs": total_utilisateurs,
        },
        "decisions": {
            "accordes": accordes,
            "refuses": refuses,
            "taux_acceptation": taux_acceptation,
        },
        "repartition_risque": risque,
        "probabilite_moyenne_defaut": proba_moyenne,
        "resultats_reels_connus": resultats_connus,
        "modele_production": modele_production,
        "evolution": evolution,
        "activite_recente": activite_recente,
    }
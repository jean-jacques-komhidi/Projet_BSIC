# -*- coding: utf-8 -*-
"""
Route du tableau de bord (statistiques).

  - GET /dashboard?periode=7j|30j|tout : statistiques agregees (agent ou admin)

Fournit une vue d'ensemble sur la periode choisie : nombre d'analyses, taux
d'accord, probabilite moyenne de defaut, issues reelles renseignees,
decisions par tranche de montant, repartition des risques, evolution, dossiers
a suivre et activite recente.

Les dates sont stockees en UTC ; elles sont converties a l'heure du Tchad
(UTC+1) pour le regroupement par jour et l'affichage.
"""

import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .security import utilisateur_courant

router = APIRouter(prefix="/dashboard", tags=["Tableau de bord"])

DECALAGE_TCHAD = timedelta(hours=1)          # N'Djamena : UTC+1, sans heure d'ete
DELAI_SUIVI_JOURS = 30                       # issue attendue apres 30 jours
NB_DOSSIERS_A_SUIVRE = 5
NB_ACTIVITE_RECENTE = 5

# Tranches de montant demande (FCFA) : (libelle, borne basse incluse, borne haute exclue)
TRANCHES_MONTANT = [
    ("Moins de 1 M", 0, 1_000_000),
    ("1 à 3 M", 1_000_000, 3_000_000),
    ("3 à 5 M", 3_000_000, 5_000_000),
    ("Plus de 5 M", 5_000_000, None),
]
PERIODES = {"7j": 7, "30j": 30, "tout": None}


def _locale(date_utc):
    return date_utc + DECALAGE_TCHAD if date_utc else None


def _dossier(analyse) -> dict:
    try:
        return json.loads(analyse.donnees_dossier) if analyse.donnees_dossier else {}
    except (ValueError, TypeError):
        return {}


def _montant(analyse):
    try:
        return float(_dossier(analyse).get("AMT_CREDIT"))
    except (TypeError, ValueError):
        return None


def _tranche(montant):
    if montant is None:
        return None
    for libelle, bas, haut in TRANCHES_MONTANT:
        if montant >= bas and (haut is None or montant < haut):
            return libelle
    return None


def _evolution(analyses, periode, maintenant_local):
    """Analyses et probabilite moyenne de defaut par jour (7j / 30j),
    ou par mois sur les 12 derniers mois (tout)."""
    if PERIODES[periode]:
        nb_jours = PERIODES[periode]
        cles = [(maintenant_local.date() - timedelta(days=i)) for i in range(nb_jours - 1, -1, -1)]
        libelle = lambda d: d.strftime("%d/%m")
        cle_de = lambda a: _locale(a.date_analyse).date()
    else:
        cles, annee, mois = [], maintenant_local.year, maintenant_local.month
        for _ in range(12):
            cles.insert(0, (annee, mois))
            mois -= 1
            if mois == 0:
                annee, mois = annee - 1, 12
        libelle = lambda c: f"{c[1]:02d}/{c[0]}"
        cle_de = lambda a: (_locale(a.date_analyse).year, _locale(a.date_analyse).month)

    groupes = {c: [] for c in cles}
    for a in analyses:
        if a.date_analyse:
            c = cle_de(a)
            if c in groupes:
                groupes[c].append(a.probabilite_defaut or 0)
    return [{
        "jour": libelle(c),
        "analyses": len(groupes[c]),
        "risque_moyen": round(sum(groupes[c]) / len(groupes[c]) * 100, 1) if groupes[c] else None,
    } for c in cles]


@router.get("")
def tableau_de_bord(
    periode: str = Query("30j", pattern="^(7j|30j|tout)$"),
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Renvoie les statistiques agregees sur la periode. Accessible a tout utilisateur connecte."""
    maintenant = datetime.utcnow()
    maintenant_local = _locale(maintenant)

    requete = db.query(models.Analyse)
    if PERIODES[periode]:
        # Debut de la periode : minuit (heure du Tchad) il y a N-1 jours
        debut_local = datetime.combine(
            maintenant_local.date() - timedelta(days=PERIODES[periode] - 1), datetime.min.time())
        requete = requete.filter(models.Analyse.date_analyse >= debut_local - DECALAGE_TCHAD)
    analyses = requete.all()

    total = len(analyses)
    accordes = [a for a in analyses if a.decision == "ACCORDE"]
    refuses = [a for a in analyses if a.decision == "REFUSE"]
    issues_connues = [a for a in accordes if a.resultat_reel in ("rembourse", "defaut")]
    probas = [a.probabilite_defaut for a in analyses if a.probabilite_defaut is not None]

    # Decisions par tranche de montant demande
    par_tranche = {libelle: {"tranche": libelle, "accordes": 0, "refuses": 0}
                   for libelle, _, _ in TRANCHES_MONTANT}
    for a in analyses:
        t = _tranche(_montant(a))
        if t:
            par_tranche[t]["accordes" if a.decision == "ACCORDE" else "refuses"] += 1

    risque = {niveau: sum(1 for a in analyses if a.classe_risque == niveau)
              for niveau in ("faible", "moyen", "eleve")}

    version = db.query(models.ModelVersion).filter(models.ModelVersion.en_production == True).first()

    # Dossiers a suivre : credits accordes depuis plus de 30 jours, issue inconnue
    # (toutes periodes confondues ; un agent ne voit que ses propres dossiers)
    suivi = db.query(models.Analyse).filter(
        models.Analyse.decision == "ACCORDE",
        models.Analyse.resultat_reel.is_(None),
        models.Analyse.date_analyse < maintenant - timedelta(days=DELAI_SUIVI_JOURS),
    )
    if utilisateur.role != "admin":
        suivi = suivi.filter(models.Analyse.user_id == utilisateur.id)
    nb_a_suivre = suivi.count()
    a_suivre = suivi.order_by(models.Analyse.date_analyse.asc()).limit(NB_DOSSIERS_A_SUIVRE).all()

    recentes = db.query(models.Analyse).order_by(
        models.Analyse.date_analyse.desc()).limit(NB_ACTIVITE_RECENTE).all()

    # Noms des clients en une seule requete
    ids_clients = {a.client_id for a in a_suivre + recentes if a.client_id}
    noms = dict(db.query(models.Client.id, models.Client.nom)
                .filter(models.Client.id.in_(ids_clients)).all()) if ids_clients else {}

    def date_txt(a, fmt):
        return _locale(a.date_analyse).strftime(fmt) if a.date_analyse else None

    return {
        "periode": periode,
        "totaux": {
            "clients": db.query(models.Client).count(),
            "analyses": total,
            "utilisateurs": db.query(models.User).count(),
        },
        "decisions": {
            "accordes": len(accordes),
            "refuses": len(refuses),
            "taux_acceptation": round(100 * len(accordes) / total, 1) if total else 0,
        },
        "decisions_par_montant": list(par_tranche.values()),
        "repartition_risque": risque,
        "probabilite_moyenne_defaut": round(sum(probas) / len(probas) * 100, 1) if probas else 0,
        "issues_reelles": {
            "renseignees": len(issues_connues),
            "credits_accordes": len(accordes),
        },
        # Conserve pour compatibilite
        "resultats_reels_connus": len(issues_connues),
        "modele_production": {
            "algorithme": version.algorithme if version else None,
            "auc": version.auc if version else None,
        },
        "evolution": _evolution(analyses, periode, maintenant_local),
        "dossiers_a_suivre": {
            "total": nb_a_suivre,
            "delai_jours": DELAI_SUIVI_JOURS,
            "liste": [{
                "id": a.id,
                "nom_client": noms.get(a.client_id, "—"),
                "date": date_txt(a, "%d/%m/%Y"),
                "jours": (maintenant - a.date_analyse).days if a.date_analyse else None,
                "montant": _montant(a),
            } for a in a_suivre],
        },
        "activite_recente": [{
            "id": a.id,
            "nom_client": noms.get(a.client_id, "—"),
            "revenu": _dossier(a).get("AMT_INCOME_TOTAL"),
            "decision": a.decision,
            "classe_risque": a.classe_risque,
            "probabilite_defaut": round((a.probabilite_defaut or 0) * 100, 1),
            "date": date_txt(a, "%d/%m %H:%M"),
        } for a in recentes],
    }

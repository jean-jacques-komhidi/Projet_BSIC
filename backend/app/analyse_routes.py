# -*- coding: utf-8 -*-
"""
Routes de gestion des analyses de credit enregistrees.

  - POST /analyses                  : realiser et enregistrer une analyse
  - GET  /analyses                  : lister toutes les analyses
  - GET  /analyses/{id}             : voir une analyse precise
  - GET  /analyses/client/{id}      : lister les analyses d'un client
  - PUT  /analyses/{id}/resultat    : renseigner le resultat reel (admin)
  - POST /analyses/{id}/simulation  : tester d'autres conditions (rien n'est enregistre)
  - DELETE /analyses/{id}           : supprimer une analyse (admin)

Chaque analyse enregistre le score, la decision, l'explication, ET les donnees
du dossier (pour un eventuel reentrainement). Le resultat reel (rembourse /
defaut) est renseigne a posteriori, une fois l'issue du credit connue.
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .schemas_analyse import AnalyseCreation, AnalyseReponse, SimulationDemande
from .security import utilisateur_courant, administrateur_courant
from .model_service import ServiceModele, SEUIL_DECISION
from .logging_config import logger
from .notification_service import creer_notification
from .pdf_service import (
    _facteurs_affiches, _ratios, _conditions_ou_recommandations, _motivation,
    _traduire, _fcfa, NORME_ENDETTEMENT,
)

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

def _analyse_avec_facteurs(analyse):
    """Transforme une analyse en dict avec les facteurs SHAP decodes."""
    facteurs = []
    if analyse.facteurs_explicatifs:
        try:
            facteurs = json.loads(analyse.facteurs_explicatifs)
        except Exception:
            facteurs = []
    return {
        "id": analyse.id,
        "client_id": analyse.client_id,
        "user_id": analyse.user_id,
        "probabilite_defaut": analyse.probabilite_defaut,
        "classe_risque": analyse.classe_risque,
        "decision": analyse.decision,
        "explication": analyse.explication,
        "facteurs_explicatifs": facteurs,
        "resultat_reel": analyse.resultat_reel,
        "model_version_id": analyse.model_version_id,
        "date_analyse": analyse.date_analyse,
    }


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
    return _analyse_avec_facteurs(analyse)


# --- READ : lister toutes les analyses ---
def _montant(analyse):
    try:
        return float(json.loads(analyse.donnees_dossier or "{}").get("AMT_CREDIT"))
    except (TypeError, ValueError):
        return None


@router.get("", response_model=list[AnalyseReponse])
def lister_analyses(
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    analyses = db.query(models.Analyse).order_by(models.Analyse.date_analyse.desc()).all()
    # Noms des clients et des agents en deux requetes (au lieu d'une par ligne)
    clients = dict(db.query(models.Client.id, models.Client.nom).all())
    agents = dict(db.query(models.User.id, models.User.nom).all())
    resultat = []
    for a in analyses:
        d = _analyse_avec_facteurs(a)
        d["nom_client"] = clients.get(a.client_id)
        d["nom_agent"] = agents.get(a.user_id)
        d["montant"] = _montant(a)
        resultat.append(d)
    return resultat


# --- READ : voir une analyse precise ---
def _nombre(valeur):
    try:
        return float(valeur)
    except (TypeError, ValueError):
        return None


def _appreciation(variable: str, dossier: dict):
    """Appreciation en mots de la valeur d'un facteur (ou None)."""
    if variable.startswith("EXT_SOURCE"):
        v = _nombre(dossier.get(variable[:12]))
        if v is None:
            return None
        for borne, mot in ((0.2, "très faible"), (0.4, "faible"), (0.6, "moyenne"), (0.8, "bonne")):
            if v < borne:
                return mot
        return "très bonne"
    if variable.startswith("ANCIENNETE_EMPLOI"):
        v = _nombre(dossier.get("ANCIENNETE_EMPLOI_ANNEES"))
        if v is not None:
            return "récente" if v < 2 else "stable" if v < 8 else "solide"
    return None


# Elements compares entre deux analyses d'un meme client :
# (cle, libelle, nature, une hausse est-elle defavorable ?)
COMPARAISONS = [
    ("AMT_CREDIT", "Montant demandé", "fcfa", True),
    ("AMT_ANNUITY", "Échéance", "fcfa", True),
    ("AMT_INCOME_TOTAL", "Revenu", "fcfa", False),
    ("ENDETTEMENT", "Taux d'endettement", "pct", True),
    ("ANCIENNETE_EMPLOI_ANNEES", "Ancienneté d'emploi", "ans", False),
    ("CNT_FAM_MEMBERS", "Personnes dans le foyer", "nb", True),
    ("EXT_SOURCE_1", "Note de solvabilité externe 1", "note", False),
    ("EXT_SOURCE_2", "Note de solvabilité externe 2", "note", False),
    ("EXT_SOURCE_3", "Note de solvabilité externe 3", "note", False),
]


def _valeurs_comparables(dossier: dict) -> dict:
    v = {cle: _nombre(dossier.get(cle)) for cle, *_ in COMPARAISONS if cle != "ENDETTEMENT"}
    if v.get("AMT_ANNUITY") and v.get("AMT_INCOME_TOTAL"):
        v["ENDETTEMENT"] = v["AMT_ANNUITY"] / v["AMT_INCOME_TOTAL"]
    return v


def _texte(valeur, nature):
    if valeur is None:
        return "—"
    if nature == "fcfa":
        return _fcfa(valeur)
    if nature == "pct":
        return f"{valeur * 100:.0f} %"
    if nature == "ans":
        return f"{valeur:.1f}".replace(".", ",").replace(",0", "") + " ans"
    if nature == "note":
        return f"{valeur:.2f}".replace(".", ",") + " / 1"
    return f"{int(valeur)}"


def _changements(precedente, dossier: dict) -> dict:
    """Ce qui a change par rapport a l'analyse precedente du meme client."""
    try:
        avant = _valeurs_comparables(json.loads(precedente.donnees_dossier or "{}"))
    except (TypeError, ValueError):
        return None
    apres = _valeurs_comparables(dossier)
    lignes = []
    for cle, libelle, nature, hausse_defavorable in COMPARAISONS:
        a, b = avant.get(cle), apres.get(cle)
        if a is None or b is None:
            continue
        ecart = b - a
        significatif = (abs(ecart) >= 0.05) if nature in ("note", "pct") else \
            (abs(ecart) >= 1) if nature == "nb" else \
            (abs(ecart) >= 1) if nature == "ans" else (a and abs(ecart) / a >= 0.10)
        if not significatif:
            continue
        lignes.append({
            "libelle": libelle, "avant": _texte(a, nature), "apres": _texte(b, nature),
            "sens": "hausse" if ecart > 0 else "baisse",
            "defavorable": (ecart > 0) == hausse_defavorable,
        })
    return {"id": precedente.id, "date": precedente.date_analyse,
            "probabilite_defaut": precedente.probabilite_defaut, "lignes": lignes}


def _detail(analyse, db: Session) -> dict:
    """Informations de la page de detail, calculees comme sur la fiche PDF
    (memes libelles, memes indicateurs, genre jamais presente comme facteur)."""
    try:
        dossier = json.loads(analyse.donnees_dossier or "{}")
    except (TypeError, ValueError):
        dossier = {}
    accorde = analyse.decision == "ACCORDE"
    facteurs = _facteurs_affiches(analyse, dossier, nombre=6)
    for f in facteurs:
        f["appreciation"] = _appreciation(f["variable"], dossier)
    ratios = _ratios(dossier)
    titre, lignes = _conditions_ou_recommandations(accorde, facteurs, ratios)

    def montant(cle):
        return _fcfa(dossier.get(cle)) if dossier.get(cle) not in (None, "") else "—"

    age = dossier.get("AGE_ANNEES")
    anciennete = dossier.get("ANCIENNETE_EMPLOI_ANNEES")
    precedentes = db.query(models.Analyse).filter(
        models.Analyse.client_id == analyse.client_id
    ).order_by(models.Analyse.date_analyse.asc()).all() if analyse.client_id else [analyse]

    return {
        "credit": [
            ["Montant demandé", montant("AMT_CREDIT")],
            ["Échéance", montant("AMT_ANNUITY")],
            ["Nombre d'échéances", str(ratios["echeances"]) if ratios["echeances"] else "—"],
            ["Prix du bien financé", montant("AMT_GOODS_PRICE")],
            ["Type de crédit", _traduire(dossier.get("NAME_CONTRACT_TYPE"))],
        ],
        "client": [
            ["Revenu", montant("AMT_INCOME_TOTAL")],
            ["Âge", f"{int(float(age))} ans" if age not in (None, "") else "—"],
            ["Situation familiale", _traduire(dossier.get("NAME_FAMILY_STATUS"))],
            ["Type de revenu", _traduire(dossier.get("NAME_INCOME_TYPE"))],
            ["Profession", _traduire(dossier.get("OCCUPATION_TYPE"))],
            ["Employeur", _traduire(dossier.get("ORGANIZATION_TYPE"))],
            ["Ancienneté d'emploi",
             (f"{float(anciennete):.1f}".replace(".", ",").replace(",0", "") + " ans")
             if anciennete not in (None, "") else "—"],
        ],
        "endettement": ratios["endettement"],
        "norme_endettement": NORME_ENDETTEMENT,
        "facteurs": facteurs,
        "motivation": _motivation(accorde, analyse.probabilite_defaut or 0, facteurs),
        "changements": _changements(precedentes[precedentes.index(analyse) - 1], dossier)
        if analyse in precedentes and precedentes.index(analyse) > 0 else None,
        "conseils": {"titre": titre.capitalize(), "lignes": lignes},
        "historique_client": [{
            "id": a.id,
            "date": a.date_analyse,
            "probabilite_defaut": a.probabilite_defaut,
            "decision": a.decision,
            "resultat_reel": a.resultat_reel,
            "montant": _montant(a),
        } for a in precedentes],
    }


@router.get("/{analyse_id}", response_model=AnalyseReponse)
def voir_analyse(
    analyse_id: int,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    analyse = db.query(models.Analyse).filter(models.Analyse.id == analyse_id).first()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    d = _analyse_avec_facteurs(analyse)
    client = db.query(models.Client).filter(models.Client.id == analyse.client_id).first()
    agent = db.query(models.User).filter(models.User.id == analyse.user_id).first()
    d["nom_client"] = client.nom if client else None
    d["nom_agent"] = agent.nom if agent else None
    d["montant"] = _montant(analyse)
    d["detail"] = _detail(analyse, db)
    return d


# --- SIMULATION : « Et si... ? » (rien n'est enregistre) ---
def _resultat_simule(proba, montant, duree, revenu):
    echeance = montant / duree
    return {
        "probabilite_defaut": proba,
        "classe_risque": service.classe_risque(proba),
        "decision": "REFUSE" if proba >= SEUIL_DECISION else "ACCORDE",
        "montant": montant, "duree_mois": duree, "echeance": round(echeance),
        "endettement": echeance / revenu if revenu else None,
    }


@router.post("/{analyse_id}/simulation")
def simuler(
    analyse_id: int,
    demande: SimulationDemande,
    db: Session = Depends(get_db),
    utilisateur: models.User = Depends(utilisateur_courant),
):
    """Recalcule la probabilite de defaut du dossier avec un autre montant et une
    autre duree, et cherche des conditions qui seraient acceptees. L'echeance est
    estimee hors interets (montant / duree). Rien n'est enregistre."""
    analyse = db.query(models.Analyse).filter(models.Analyse.id == analyse_id).first()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    try:
        dossier = json.loads(analyse.donnees_dossier or "{}")
    except (TypeError, ValueError):
        dossier = {}
    if not dossier:
        raise HTTPException(status_code=400, detail="Dossier indisponible pour cette analyse")
    revenu = _nombre(dossier.get("AMT_INCOME_TOTAL"))

    def variante(montant, duree):
        d = dict(dossier)
        d["AMT_CREDIT"] = montant
        d["AMT_ANNUITY"] = montant / duree
        return d

    montant, duree = demande.montant, demande.duree_mois
    proba = service.predire(variante(montant, duree))
    resultat = _resultat_simule(proba, montant, duree, revenu)

    # Pistes : montant maximal accorde a duree egale ; duree minimale a montant egal
    pistes = []
    # (au plus une baisse a 30 % du montant : au-dela, ce n est plus le meme projet)
    montants = [round(montant * k / 20, -4) for k in range(20, 5, -1)]
    probas = service.predire_lot([variante(m, duree) for m in montants])
    m_ok = next((m for m, p in zip(montants, probas) if p < SEUIL_DECISION), None)
    if m_ok and m_ok < montant:
        pistes.append({"type": "montant", **_resultat_simule(
            probas[montants.index(m_ok)], m_ok, duree, revenu)})
    durees = [n for n in range(duree + 6, 121, 6)]
    probas = service.predire_lot([variante(montant, n) for n in durees])
    n_ok = next((n for n, p in zip(durees, probas) if p < SEUIL_DECISION), None)
    if n_ok:
        pistes.append({"type": "duree", **_resultat_simule(
            probas[durees.index(n_ok)], montant, n_ok, revenu)})
    resultat["pistes"] = pistes if proba >= SEUIL_DECISION else []
    return resultat


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
    if analyse.decision != "ACCORDE":
        raise HTTPException(status_code=400,
                            detail="Un credit refuse n'a pas d'issue a renseigner")

    analyse.resultat_reel = resultat
    db.commit()
    db.refresh(analyse)
    return analyse


# --- DELETE : supprimer une analyse (administrateur uniquement) ---
@router.delete("/{analyse_id}", status_code=204)
def supprimer_analyse(
    analyse_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(administrateur_courant),
):
    """Supprime definitivement une analyse (saisie en double, erreur de dossier...).
    Reserve a l'administrateur ; la suppression est tracee dans le journal et
    signalee par une notification."""
    analyse = db.query(models.Analyse).filter(models.Analyse.id == analyse_id).first()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    client = db.query(models.Client).filter(models.Client.id == analyse.client_id).first()
    nom = client.nom if client else "client inconnu"
    date = analyse.date_analyse.strftime("%d/%m/%Y") if analyse.date_analyse else "?"
    db.delete(analyse)
    db.commit()
    logger.warning(f"Analyse {analyse_id} ({nom}, {date}) supprimee par {admin.email}")
    creer_notification(db, "Analyse supprimée",
                       f"L'analyse n° {analyse_id} de {nom} du {date} a été supprimée par {admin.nom}.",
                       "alerte")
    return Response(status_code=204)


# --- EXPORT PDF : telecharger la fiche de decision ---
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
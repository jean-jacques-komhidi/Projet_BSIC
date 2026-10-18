# -*- coding: utf-8 -*-
"""
Alertes automatiques du monitoring.

La verification ne depend pas de l'ouverture d'une page : elle est lancee au
demarrage du serveur et apres chaque nouvelle analyse, au plus une fois par
jour. Pour ne pas inonder l'administrateur, on ne notifie que lorsque l'etat
change (stable -> a surveiller -> reentrainement recommande -> retour a la
normale), avec un rappel apres 7 jours si l'alerte persiste.

Un rappel hebdomadaire signale aussi les credits dont l'issue reste a
renseigner : sans issues reelles, la performance ne peut pas etre mesuree.

Les notifications previennent ; elles ne declenchent jamais le reentrainement,
qui reste une decision de l'administrateur.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from . import models
from .logging_config import logger
from .notification_service import notifier_admins, creer_notification

INTERVALLE_VERIFICATION = timedelta(hours=24)
RAPPEL_ALERTE = timedelta(days=7)
RAPPEL_ISSUES = timedelta(days=7)
LIEN_MONITORING = ("/monitoring", "Ouvrir le monitoring")


def _lire(db: Session, cle: str):
    ligne = db.get(models.EtatSurveillance, cle)
    return ligne


def _ecrire(db: Session, cle: str, valeur: str = None):
    ligne = db.get(models.EtatSurveillance, cle)
    if ligne is None:
        ligne = models.EtatSurveillance(cle=cle)
        db.add(ligne)
    ligne.valeur = valeur
    ligne.date_maj = datetime.utcnow()


def _texte_conditions(etat) -> str:
    atteintes = [c for c in etat["regle"]["conditions"] if c["atteinte"]]
    return " ; ".join(f"{c['titre'][0].lower()}{c['titre'][1:]} ({c['detail']})" for c in atteintes)


def _notifier_etat(db: Session, etat: dict, ancien: str, rappel: bool = False):
    nouveau = etat["etat"]
    lien, texte_lien = LIEN_MONITORING
    options = {"categorie": "modele", "lien": lien, "texte_lien": texte_lien}
    if nouveau == "alerte":
        n = etat["regle"]["atteintes"]
        notifier_admins(db, "Rappel : réentraînement recommandé" if rappel else "Réentraînement recommandé",
                        f"{n} condition{'s' if n > 1 else ''} sur 3 atteinte{'s' if n > 1 else ''} : "
                        f"{_texte_conditions(etat)}.", type="danger", **options)
    elif nouveau == "surveiller":
        v = etat["donnees"]["detail"]
        if v and v["niveau"] != "stable":
            message = (f"PSI de {v['psi']:.2f} sur « {v['libelle'].lower()} » entre la référence et les "
                       f"30 derniers jours. À surveiller.").replace(".", ",", 1)
            titre = f"Dérive {'forte' if v['niveau'] == 'forte' else 'modérée'} sur « {v['libelle'].lower()} »"
        else:
            p = etat["predictions"]
            message = (f"La répartition des scores a changé (PSI {p['psi']:.2f}). Taux de refus : "
                       f"{p['taux_refus_reference']:.0f} % en référence, {p['taux_refus_recent']:.0f} % récemment.").replace(".", ",", 1)
            titre = "Les prédictions du modèle évoluent"
        notifier_admins(db, titre, message, type="alerte", **options)
    elif nouveau == "ok" and ancien in ("alerte", "surveiller"):
        notifier_admins(db, "Le modèle est revenu sous contrôle",
                        "Plus aucune dérive significative ni baisse de performance n'est détectée.",
                        type="succes", **options)


def verifier_et_notifier(db: Session, forcer: bool = False):
    """Recalcule l'etat du modele et previent les administrateurs si besoin.

    Renvoie l'etat calcule (ou None si la verification du jour a deja eu lieu)."""
    from .surveillance_service import etat_du_modele

    maintenant = datetime.utcnow()
    derniere = _lire(db, "derniere_verification")
    if not forcer and derniere and derniere.date_maj and maintenant - derniere.date_maj < INTERVALLE_VERIFICATION:
        return None

    etat = etat_du_modele(db)
    precedent = _lire(db, "etat")
    ancien = precedent.valeur if precedent else None
    nouveau = etat["etat"]

    if nouveau != "insuffisant":
        if nouveau != ancien:
            _notifier_etat(db, etat, ancien)
            _ecrire(db, "etat", nouveau)
            _ecrire(db, "dernier_rappel_alerte", nouveau)
        elif nouveau == "alerte":
            rappel = _lire(db, "dernier_rappel_alerte")
            if rappel and rappel.date_maj and maintenant - rappel.date_maj >= RAPPEL_ALERTE:
                _notifier_etat(db, etat, ancien, rappel=True)
                _ecrire(db, "dernier_rappel_alerte", nouveau)

    # Rappel hebdomadaire des issues a renseigner
    en_attente = etat["performance"]["issues_en_attente"]
    rappel_issues = _lire(db, "rappel_issues")
    if en_attente and (rappel_issues is None or rappel_issues.date_maj is None
                       or maintenant - rappel_issues.date_maj >= RAPPEL_ISSUES):
        notifier_admins(db, f"{en_attente} issue{'s' if en_attente > 1 else ''} à renseigner",
                        f"{en_attente} crédit{'s' if en_attente > 1 else ''} accordé{'s' if en_attente > 1 else ''} "
                        f"depuis plus de 30 jours attend{'ent' if en_attente > 1 else ''} leur issue (remboursé ou défaut). "
                        "Sans elles, la performance réelle du modèle ne peut pas être mesurée.",
                        type="alerte", categorie="dossiers", lien="/historique?issue=a_renseigner",
                        texte_lien="Renseigner les issues")
        _ecrire(db, "rappel_issues", str(en_attente))

    _ecrire(db, "derniere_verification", nouveau)
    db.commit()
    logger.info(f"Surveillance du modele : etat {nouveau} (avant : {ancien}).")
    return etat


def verifier_en_tache_de_fond():
    """Verification lancee apres une analyse ou au demarrage (sa propre session)."""
    from .database import SessionLocal
    db = SessionLocal()
    try:
        verifier_et_notifier(db)
    except Exception as e:   # la surveillance ne doit jamais bloquer l'application
        logger.error(f"Surveillance du modele impossible : {e}")
    finally:
        db.close()


def alerter_client_en_hausse(db: Session, analyse):
    """Previent l'agent si le risque du client monte depuis trois analyses."""
    if not analyse.client_id:
        return
    dernieres = db.query(models.Analyse).filter(models.Analyse.client_id == analyse.client_id) \
        .order_by(models.Analyse.date_analyse.desc()).limit(3).all()
    if len(dernieres) < 3:
        return
    p = [a.probabilite_defaut for a in reversed(dernieres)]
    if not (p[1] - p[0] >= 0.03 and p[2] - p[1] >= 0.03):
        return
    client = db.get(models.Client, analyse.client_id)
    nom = client.nom if client else "ce client"
    suite = ", puis ".join(f"{round(x * 100)} %" for x in p)
    creer_notification(
        db, f"Client à risque en hausse : {nom}",
        f"Son risque augmente depuis trois analyses : {suite}. Vérifiez sa situation avant tout nouvel engagement.",
        type="alerte", destinataire_id=analyse.user_id, categorie="dossiers",
        lien=f"/analyse/{analyse.id}", texte_lien="Voir le dossier")

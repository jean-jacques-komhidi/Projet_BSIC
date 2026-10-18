# -*- coding: utf-8 -*-
"""
Surveillance du modele de scoring (monitoring).

Trois niveaux sont surveilles, tous calcules sur les analyses enregistrees dans
l'application (memes unites, en FCFA, meme saisie) :

1. Les donnees (data drift) : pour chaque variable, l'indice de stabilite de la
   population (PSI) compare la repartition des dossiers de reference (les
   analyses de plus de 30 jours) a celle des 30 derniers jours.
       PSI = somme sur les tranches de (recent - reference) x ln(recent / reference)
       < 0,10 : stable ; 0,10 a 0,25 : derive moderee ; > 0,25 : derive forte
   Avec peu de dossiers, le PSI varie beaucoup par simple hasard. On verifie
   donc aussi que l'ecart est statistiquement significatif : sans changement
   reel, PSI x n1.n2/(n1+n2) suit approximativement une loi du khi-deux a
   (tranches - 1) degres de liberte. Une derive n'est retenue que si p < 0,05.
2. Les predictions : PSI de la repartition des probabilites de defaut et
   evolution du taux de refus.
3. La performance reelle : sur les credits accordes dont l'issue est connue,
   AUC et comparaison du defaut predit au defaut constate, par mois d'octroi.

Une regle fixee a l'avance recommande le reentrainement. La decision reste
humaine : l'administrateur lance le reentrainement, et le nouveau modele ne
remplace l'actuel que s'il fait mieux.
"""

import json
import math
from datetime import datetime, timedelta

import numpy as np
from scipy.stats import chi2
from sklearn.metrics import roc_auc_score
from sqlalchemy.orm import Session

from . import models

# Variables surveillees : (cle, libelle, nature, importante pour la regle, unite)
VARIABLES = [
    ("EXT_SOURCE_1", "Note de solvabilité externe 1", "num", True, "note"),
    ("EXT_SOURCE_2", "Note de solvabilité externe 2", "num", True, "note"),
    ("EXT_SOURCE_3", "Note de solvabilité externe 3", "num", True, "note"),
    ("AMT_INCOME_TOTAL", "Revenu", "num", True, "fcfa"),
    ("AMT_CREDIT", "Montant demandé", "num", True, "fcfa"),
    ("AMT_ANNUITY", "Échéance", "num", True, "fcfa"),
    ("AGE_ANNEES", "Âge", "num", False, "ans"),
    ("ANCIENNETE_EMPLOI_ANNEES", "Ancienneté d'emploi", "num", False, "ans"),
    ("NAME_INCOME_TYPE", "Type de revenu", "cat", False, None),
    ("OCCUPATION_TYPE", "Profession", "cat", False, None),
]
CATEGORIES_FR = {
    "Working": "Salarié", "Commercial associate": "Associé commercial", "State servant": "Fonctionnaire",
    "Pensioner": "Retraité", "Accountants": "Comptable", "Core staff": "Personnel qualifié",
    "Managers": "Cadre", "Drivers": "Chauffeur", "Sales staff": "Commercial", "Laborers": "Ouvrier",
}

SEUIL_MODERE = 0.10
SEUIL_FORT = 0.25
JOURS_RECENT = 30
MIN_ANALYSES = 30          # par periode, pour que le PSI ait un sens
MIN_ISSUES = 50            # issues reelles necessaires pour juger la performance
SEUIL_AUC = 0.70           # AUC reelle sous laquelle on alerte
BAISSE_AUC_MAX = 0.05      # baisse toleree par rapport a l'AUC d'entrainement
ECART_DEFAUT_MAX = 0.08    # ecart tolere entre defaut predit et constate
MOIS_PERFORMANCE = 6
DECALAGE_TCHAD = timedelta(hours=1)
EPS = 1e-4


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------
def psi(reference, recent) -> float:
    """Indice de stabilite entre deux repartitions (listes de proportions)."""
    total = 0.0
    for r, c in zip(reference, recent):
        r, c = max(r, EPS), max(c, EPS)
        total += (c - r) * math.log(c / r)
    return round(total, 3)


def p_valeur(valeur, n_ref, n_rec, nb_tranches):
    """Probabilite d'observer un tel PSI par simple hasard (aucun changement reel)."""
    if not n_ref or not n_rec or nb_tranches < 2:
        return 1.0
    statistique = valeur * n_ref * n_rec / (n_ref + n_rec)
    return float(chi2.sf(statistique, nb_tranches - 1))


def nb_tranches(n_ref, n_rec):
    """Deciles si les deux periodes sont assez fournies, sinon quintiles (moins de bruit)."""
    return 10 if min(n_ref, n_rec) >= 200 else 5


def niveau(valeur, significatif=True) -> str:
    if valeur is None:
        return "inconnu"
    if not significatif:
        return "stable"
    if valeur >= SEUIL_FORT:
        return "forte"
    if valeur >= SEUIL_MODERE:
        return "moderee"
    return "stable"


def _nombre(v):
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _format(v, unite) -> str:
    if unite == "fcfa":
        if v >= 1_000_000:
            return f"{v / 1_000_000:.1f}".replace(".", ",").replace(",0", "") + " M"
        return f"{round(v / 1000):.0f} k"
    if unite == "note":
        return f"{v:.2f}".replace(".", ",")
    return f"{v:.0f}"


def _proportions(indices, nb):
    compte = np.bincount(np.asarray(indices, dtype=int), minlength=nb)
    total = compte.sum()
    return (compte / total).tolist() if total else [0.0] * nb


def _repartition_numerique(ref, rec, unite):
    """Tranches de meme effectif dans la reference ; renvoie libelles et proportions."""
    k = nb_tranches(len(ref), len(rec))
    bornes = np.unique(np.quantile(ref, np.linspace(0, 1, k + 1)[1:-1]))
    nb = len(bornes) + 1
    p_ref = _proportions(np.digitize(ref, bornes, right=True), nb)
    p_rec = _proportions(np.digitize(rec, bornes, right=True), nb)
    libelles = []
    for i in range(nb):
        if i == 0:
            libelles.append("≤ " + _format(bornes[0], unite))
        elif i == nb - 1:
            libelles.append("> " + _format(bornes[-1], unite))
        else:
            libelles.append(_format(bornes[i - 1], unite) + " à " + _format(bornes[i], unite))
    return libelles, p_ref, p_rec


def _repartition_categorielle(ref, rec):
    categories = sorted(set(ref) | set(rec), key=lambda c: -ref.count(c))
    p_ref = [ref.count(c) / len(ref) for c in categories]
    p_rec = [rec.count(c) / len(rec) for c in categories]
    return [CATEGORIES_FR.get(c, c) for c in categories], p_ref, p_rec


def _dossier(analyse) -> dict:
    try:
        return json.loads(analyse.donnees_dossier or "{}")
    except (TypeError, ValueError):
        return {}


def _locale(d):
    return d + DECALAGE_TCHAD


def _auc(y, p):
    if len(y) < 10 or len(set(y)) < 2:
        return None
    return round(float(roc_auc_score(y, p)), 3)


# ---------------------------------------------------------------------------
# 1. Derive des donnees
# ---------------------------------------------------------------------------
def _derive_donnees(ref_dossiers, rec_dossiers):
    variables = []
    for cle, libelle, nature, importante, unite in VARIABLES:
        if nature == "num":
            ref = np.array([v for v in (_nombre(d.get(cle)) for d in ref_dossiers) if v is not None])
            rec = np.array([v for v in (_nombre(d.get(cle)) for d in rec_dossiers) if v is not None])
            if len(ref) < MIN_ANALYSES or len(rec) < MIN_ANALYSES:
                continue
            tranches, p_ref, p_rec = _repartition_numerique(ref, rec, unite)
            med_ref, med_rec = float(np.median(ref)), float(np.median(rec))
        else:
            ref = [d.get(cle) for d in ref_dossiers if d.get(cle)]
            rec = [d.get(cle) for d in rec_dossiers if d.get(cle)]
            if len(ref) < MIN_ANALYSES or len(rec) < MIN_ANALYSES:
                continue
            tranches, p_ref, p_rec = _repartition_categorielle(ref, rec)
            med_ref = med_rec = None
        valeur = psi(p_ref, p_rec)
        pv = p_valeur(valeur, len(ref), len(rec), len(tranches))
        variables.append({
            "variable": cle, "libelle": libelle, "importante": importante, "unite": unite,
            "psi": valeur, "p_valeur": round(pv, 4), "significatif": pv < 0.05,
            "niveau": niveau(valeur, pv < 0.05),
            "tranches": tranches,
            "reference": [round(p * 100, 1) for p in p_ref],
            "recent": [round(p * 100, 1) for p in p_rec],
            "mediane_reference": med_ref, "mediane_recente": med_rec,
        })
    # Les derives significatives d'abord, puis par PSI decroissant
    variables.sort(key=lambda v: (not v["significatif"], -v["psi"]))
    return variables


def _phrase_detail(v):
    """Explique en une phrase le changement principal de la variable la plus touchee."""
    if not v:
        return ""
    if v["niveau"] == "stable":
        if not v["significatif"] and v["psi"] >= SEUIL_MODERE:
            return (f"Les écarts visibles sur « {v['libelle'].lower()} » restent dans ce que le hasard peut produire "
                    f"avec si peu de dossiers : pas de dérive démontrée.")
        return f"La répartition de la variable « {v['libelle'].lower()} » n'a presque pas changé."
    ecarts = [c - r for r, c in zip(v["reference"], v["recent"])]
    i = int(np.argmax(ecarts))
    return (f"{str(v['recent'][i]).replace('.', ',')} % des dossiers récents sont dans la tranche "
            f"« {v['tranches'][i]} », contre {str(v['reference'][i]).replace('.', ',')} % en référence : "
            f"la clientèle a changé et le modèle travaille sur des profils qu'il connaît moins bien.")


# ---------------------------------------------------------------------------
# 2. Derive des predictions
# ---------------------------------------------------------------------------
def _derive_predictions(ref_analyses, rec_analyses, toutes, maintenant):
    ref_p = np.array([a.probabilite_defaut for a in ref_analyses])
    rec_p = np.array([a.probabilite_defaut for a in rec_analyses])
    # Affichage : 20 tranches de 5 points de probabilite
    affichage = np.linspace(0.05, 0.95, 19)
    p_ref = _proportions(np.digitize(ref_p, affichage), 20)
    p_rec = _proportions(np.digitize(rec_p, affichage), 20)
    # Calcul du PSI : tranches de meme effectif dans la reference
    _, q_ref, q_rec = _repartition_numerique(ref_p, rec_p, "note")
    taux = lambda liste: round(100 * sum(a.decision == "REFUSE" for a in liste) / len(liste), 1) if liste else None
    semaines = []
    for k in range(11, -1, -1):
        debut, fin = maintenant - timedelta(days=7 * (k + 1)), maintenant - timedelta(days=7 * k)
        lot = [a for a in toutes if debut <= a.date_analyse < fin]
        semaines.append({"debut": _locale(debut).strftime("%d/%m"), "taux_refus": taux(lot), "analyses": len(lot)})
    valeur = psi(q_ref, q_rec)
    pv = p_valeur(valeur, len(ref_p), len(rec_p), len(q_ref))
    return {
        "psi": valeur, "p_valeur": round(pv, 4), "significatif": pv < 0.05, "niveau": niveau(valeur, pv < 0.05),
        "reference": [round(p * 100, 1) for p in p_ref],
        "recent": [round(p * 100, 1) for p in p_rec],
        "taux_refus_reference": taux(ref_analyses), "taux_refus_recent": taux(rec_analyses),
        "semaines": semaines,
    }


# ---------------------------------------------------------------------------
# 3. Performance reelle
# ---------------------------------------------------------------------------
def _performance(toutes, maintenant, version):
    debut = maintenant - timedelta(days=31 * MOIS_PERFORMANCE)
    connues = [a for a in toutes if a.decision == "ACCORDE" and a.resultat_reel in ("rembourse", "defaut")
               and a.date_analyse >= debut]
    y = [1 if a.resultat_reel == "defaut" else 0 for a in connues]
    p = [a.probabilite_defaut for a in connues]

    mois = []
    annee, m = _locale(maintenant).year, _locale(maintenant).month
    cles = []
    for _ in range(MOIS_PERFORMANCE):
        cles.insert(0, (annee, m))
        m -= 1
        if m == 0:
            annee, m = annee - 1, 12
    noms = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
    for a_, m_ in cles:
        lot = [a for a in connues if (_locale(a.date_analyse).year, _locale(a.date_analyse).month) == (a_, m_)]
        yy = [1 if a.resultat_reel == "defaut" else 0 for a in lot]
        pp = [a.probabilite_defaut for a in lot]
        mois.append({
            "mois": noms[m_ - 1], "issues": len(lot), "auc": _auc(yy, pp),
            "defaut_predit": round(100 * float(np.mean(pp)), 1) if lot else None,
            "defaut_constate": round(100 * float(np.mean(yy)), 1) if lot else None,
        })

    en_attente = sum(1 for a in toutes if a.decision == "ACCORDE" and not a.resultat_reel
                     and a.date_analyse < maintenant - timedelta(days=JOURS_RECENT))
    return {
        "issues": len(connues), "issues_minimum": MIN_ISSUES, "issues_en_attente": en_attente,
        "auc": _auc(y, p), "auc_entrainement": version.auc if version else None,
        "defaut_predit": round(100 * float(np.mean(p)), 1) if connues else None,
        "defaut_constate": round(100 * float(np.mean(y)), 1) if connues else None,
        "mois": mois,
    }


# ---------------------------------------------------------------------------
# 4. Regle de reentrainement
# ---------------------------------------------------------------------------
def _pct(x):
    return f"{x:.0f} %"


def _conditions(variables, perf):
    fortes = [v for v in variables if v["importante"] and v["niveau"] == "forte"]
    plus_haute = max((v for v in variables if v["importante"]), key=lambda v: v["psi"], default=None)
    c1 = {
        "titre": "Dérive forte sur une variable importante",
        "atteinte": bool(fortes),
        "detail": (", ".join(f"{v['libelle']} : PSI {v['psi']:.2f}".replace(".", ",") for v in fortes[:2]) + ", seuil 0,25")
        if fortes else (f"PSI le plus élevé : {plus_haute['psi']:.2f} ({plus_haute['libelle']}), seuil 0,25".replace(".", ",")
                        if plus_haute else "Pas assez d'analyses pour mesurer la dérive"),
    }
    assez = perf["issues"] >= MIN_ISSUES
    manque = f"Pas assez d'issues réelles : {perf['issues']} sur {MIN_ISSUES} nécessaires"
    auc, ref = perf["auc"], perf["auc_entrainement"]
    if assez and auc is not None and ref:
        baisse = ref - auc
        c2 = {"titre": "Baisse de l'AUC sur les issues réelles", "atteinte": baisse > BAISSE_AUC_MAX or auc < SEUIL_AUC,
              "detail": f"{ref:.3f} à l'entraînement, {auc:.2f} aujourd'hui : baisse de {max(baisse, 0):.2f}, seuil 0,05".replace(".", ",")}
    else:
        c2 = {"titre": "Baisse de l'AUC sur les issues réelles", "atteinte": False, "detail": manque}
    if assez and perf["defaut_predit"] is not None:
        ecart = perf["defaut_constate"] - perf["defaut_predit"]
        c3 = {"titre": "Écart entre défaut prédit et constaté", "atteinte": abs(ecart) > ECART_DEFAUT_MAX * 100,
              "detail": f"{_pct(perf['defaut_predit'])} prédit, {_pct(perf['defaut_constate'])} constaté : "
                        f"{abs(ecart):.0f} points d'écart, seuil 8 points"}
    else:
        c3 = {"titre": "Écart entre défaut prédit et constaté", "atteinte": False, "detail": manque}
    return [c1, c2, c3]


# ---------------------------------------------------------------------------
# Synthese
# ---------------------------------------------------------------------------
def etat_du_modele(db: Session) -> dict:
    """Calcule l'etat complet du modele (donnees, predictions, performance, regle)."""
    maintenant = datetime.utcnow()
    limite = maintenant - timedelta(days=JOURS_RECENT)
    toutes = db.query(models.Analyse).filter(models.Analyse.date_analyse.isnot(None)) \
        .order_by(models.Analyse.date_analyse.asc()).all()
    ref_analyses = [a for a in toutes if a.date_analyse < limite]
    rec_analyses = [a for a in toutes if a.date_analyse >= limite]
    version = db.query(models.ModelVersion).filter(models.ModelVersion.en_production == True).first()  # noqa: E712

    periodes = {
        "reference": {"analyses": len(ref_analyses),
                      "debut": _locale(ref_analyses[0].date_analyse).strftime("%d/%m/%Y") if ref_analyses else None,
                      "fin": _locale(ref_analyses[-1].date_analyse).strftime("%d/%m/%Y") if ref_analyses else None},
        "recente": {"analyses": len(rec_analyses), "jours": JOURS_RECENT},
        "minimum": MIN_ANALYSES,
    }
    perf = _performance(toutes, maintenant, version)
    suffisant = len(ref_analyses) >= MIN_ANALYSES and len(rec_analyses) >= MIN_ANALYSES

    variables, predictions = [], None
    if suffisant:
        ref_d = [_dossier(a) for a in ref_analyses]
        rec_d = [_dossier(a) for a in rec_analyses]
        variables = _derive_donnees(ref_d, rec_d)
        predictions = _derive_predictions(ref_analyses, rec_analyses, toutes, maintenant)

    conditions = _conditions(variables, perf)
    nb_atteintes = sum(c["atteinte"] for c in conditions)
    psi_max = variables[0]["psi"] if variables else None
    niveau_donnees = variables[0]["niveau"] if variables else "inconnu"
    if not suffisant:
        etat = "insuffisant"
    elif nb_atteintes:
        etat = "alerte"
    elif niveau_donnees != "stable" or (predictions and predictions["niveau"] != "stable"):
        etat = "surveiller"
    else:
        etat = "ok"

    return {
        "etat": etat,
        "date_calcul": _locale(maintenant).strftime("%d/%m/%Y %H:%M"),
        "periodes": periodes,
        "seuils": {"modere": SEUIL_MODERE, "fort": SEUIL_FORT, "auc": SEUIL_AUC},
        "modele": {"algorithme": version.algorithme if version else None,
                   "auc": version.auc if version else None,
                   "version": _numero_version(db, version) if version else None},
        "donnees": {"variables": variables, "psi_max": psi_max,
                    "niveau": niveau_donnees, "detail": variables[0] if variables else None,
                    "phrase": _phrase_detail(variables[0]) if variables else ""},
        "predictions": predictions,
        "performance": perf,
        "regle": {"conditions": conditions, "atteintes": nb_atteintes,
                  "reentrainement_recommande": nb_atteintes > 0},
    }


def _numero_version(db: Session, version) -> int:
    return db.query(models.ModelVersion).filter(models.ModelVersion.id <= version.id).count()


def liste_versions(db: Session, auc_reelle_production=None) -> list:
    """Versions du modele, de la plus recente a la plus ancienne."""
    versions = db.query(models.ModelVersion).order_by(models.ModelVersion.id.asc()).all()
    resultat = []
    for i, v in enumerate(versions, start=1):
        statut = "production" if v.en_production else (v.statut or "retire")
        resultat.append({
            "version": i, "algorithme": v.algorithme, "auc": v.auc,
            "auc_reelle": auc_reelle_production if v.en_production and auc_reelle_production is not None else v.auc_reelle,
            "statut": statut,
            "date": _locale(v.date_creation).strftime("%d/%m/%Y") if v.date_creation else None,
        })
    return list(reversed(resultat))

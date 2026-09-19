# -*- coding: utf-8 -*-
"""
Generation de l'explication en langage naturel a partir des facteurs SHAP.

Ce module transforme les contributions SHAP (techniques) en un texte clair
destine a l'agent de credit :
- il resume la decision,
- il liste les facteurs favorables et defavorables en francais,
- en cas de refus, il propose des pistes d'amelioration.

Cette explication est generee par regles (sans modele de langage), ce qui la
rend fiable, gratuite et instantanee. Elle pourra etre enrichie plus tard par
un modele de langage pour une formulation plus fluide.
"""


def _libelle(variable: str) -> str:
    """Traduit un nom de variable technique en libelle francais lisible."""
    # Variables numeriques
    correspondances = {
        "EXT_SOURCE_1": "le score de solvabilite",
        "EXT_SOURCE_2": "le score de solvabilite",
        "EXT_SOURCE_3": "le score de solvabilite",
        "AMT_INCOME_TOTAL": "le revenu",
        "AMT_CREDIT": "le montant du credit",
        "AMT_ANNUITY": "le montant de l'echeance",
        "AMT_GOODS_PRICE": "le prix du bien finance",
        "AGE_ANNEES": "l'age",
        "ANCIENNETE_EMPLOI_ANNEES": "l'anciennete d'emploi",
        "CNT_CHILDREN": "le nombre d'enfants",
        "CNT_FAM_MEMBERS": "la taille de la famille",
        "EMPLOI_ANORMAL": "l'absence d'emploi salarie",
    }
    for cle, libelle in correspondances.items():
        if variable.startswith(cle):
            return libelle
    # Variables categorielles (prefixe_valeur)
    if variable.startswith("CODE_GENDER"):
        return "le genre"
    if variable.startswith("NAME_FAMILY_STATUS"):
        return "la situation familiale"
    if variable.startswith("NAME_EDUCATION_TYPE"):
        return "le niveau d'education"
    if variable.startswith("OCCUPATION_TYPE"):
        return "la profession"
    if variable.startswith("ORGANIZATION_TYPE"):
        return "le type d'employeur"
    if variable.startswith("NAME_INCOME_TYPE"):
        return "le type de revenu"
    if variable.startswith("NAME_CONTRACT_TYPE"):
        return "le type de credit"
    return variable


def _conseil(variable: str) -> str:
    """Renvoie un conseil d'amelioration pour un facteur defavorable donne."""
    if variable.startswith("AMT_CREDIT") or variable.startswith("AMT_GOODS_PRICE"):
        return "reduire le montant du credit sollicite"
    if variable.startswith("AMT_ANNUITY"):
        return "allonger la duree pour reduire l'echeance mensuelle"
    if variable.startswith("EXT_SOURCE"):
        return "ameliorer son historique de credit ou fournir des garanties"
    if variable.startswith("ANCIENNETE_EMPLOI"):
        return "attendre d'avoir une plus grande anciennete professionnelle"
    if variable.startswith("AMT_INCOME_TOTAL"):
        return "justifier de revenus complementaires ou d'une domiciliation"
    return None


def generer_explication(decision: str, facteurs: list) -> str:
    """Genere le texte d'explication en langage naturel.

    - decision : "ACCORDE" ou "REFUSE"
    - facteurs : liste de dictionnaires {variable, contribution}
      (contribution positive = augmente le risque, negative = le reduit)
    """
    # Separer les facteurs favorables (reduisent le risque) et defavorables
    favorables, defavorables = [], []
    for f in facteurs:
        libelle = _libelle(f["variable"])
        if f["contribution"] < 0:
            if libelle not in favorables:
                favorables.append(libelle)
        else:
            if libelle not in defavorables:
                defavorables.append(libelle)

    phrases = []

    if decision == "ACCORDE":
        phrases.append("Le credit peut etre accorde : le dossier presente un risque de defaut maitrise.")
        if favorables:
            liste = ", ".join(favorables[:3])
            phrases.append(f"Les principaux elements favorables sont {liste}.")
        if defavorables:
            liste = ", ".join(defavorables[:2])
            phrases.append(f"Quelques points de vigilance subsistent neanmoins, notamment {liste}, sans remettre en cause la decision.")
    else:  # REFUSE
        phrases.append("Le credit est refuse en l'etat : le dossier presente un risque de defaut trop eleve.")
        if defavorables:
            liste = ", ".join(defavorables[:3])
            phrases.append(f"Les principaux facteurs de risque sont {liste}.")
        # Conseils d'amelioration bases sur les facteurs defavorables
        conseils = []
        for f in facteurs:
            if f["contribution"] > 0:
                c = _conseil(f["variable"])
                if c and c not in conseils:
                    conseils.append(c)
        if conseils:
            liste = " ; ".join(conseils[:3])
            phrases.append(f"Pour ameliorer le dossier, le demandeur pourrait : {liste}.")
        if favorables:
            liste = ", ".join(favorables[:2])
            phrases.append(f"Le dossier presente toutefois des atouts, comme {liste}.")

    return " ".join(phrases)
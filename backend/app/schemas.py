# -*- coding: utf-8 -*-
"""
Schémas de données de l'API CREDISCORE.

Ces classes définissent le format des données échangées avec l'API :
- ce que le client envoie (un dossier de crédit),
- ce que l'API renvoie (le score, la décision, l'explication).

Pydantic valide automatiquement ces formats : si une donnée manque ou a un
mauvais type, l'API renvoie une erreur claire avant même d'appeler le modèle.
"""

from pydantic import BaseModel, Field


class DossierCredit(BaseModel):
    """Données d'un dossier de crédit soumis à l'analyse.

    Ces champs correspondent exactement aux variables attendues par le modèle,
    elles-mêmes issues de la fiche de prêt de la BSIC.
    """
    # --- Profil du demandeur ---
    AGE_ANNEES: float = Field(..., ge=18, le=100, description="Âge du demandeur en années")
    CODE_GENDER: str = Field(..., description="Genre : 'M' ou 'F'")
    NAME_FAMILY_STATUS: str = Field(..., description="Situation familiale")
    CNT_CHILDREN: int = Field(..., ge=0, description="Nombre d'enfants")
    CNT_FAM_MEMBERS: float = Field(..., ge=1, description="Nombre de membres de la famille")
    NAME_EDUCATION_TYPE: str = Field(..., description="Niveau d'éducation")
    OCCUPATION_TYPE: str = Field(..., description="Profession")
    ORGANIZATION_TYPE: str = Field(..., description="Type d'employeur")
    NAME_INCOME_TYPE: str = Field(..., description="Type de revenu")
    ANCIENNETE_EMPLOI_ANNEES: float = Field(..., ge=0, description="Ancienneté d'emploi en années")
    EMPLOI_ANORMAL: int = Field(0, description="1 si sans emploi salarié (retraité), 0 sinon")

    # --- Caractéristiques du crédit et revenus ---
    AMT_INCOME_TOTAL: float = Field(..., gt=0, description="Revenu total")
    AMT_CREDIT: float = Field(..., gt=0, description="Montant du crédit sollicité")
    AMT_ANNUITY: float = Field(..., gt=0, description="Montant de l'échéance")
    AMT_GOODS_PRICE: float = Field(..., gt=0, description="Prix du bien financé")
    NAME_CONTRACT_TYPE: str = Field(..., description="Type de contrat")

    # --- Proxy de centrale des risques ---
    EXT_SOURCE_1: float = Field(None, ge=0, le=1, description="Score externe 1 (0 à 1)")
    EXT_SOURCE_2: float = Field(None, ge=0, le=1, description="Score externe 2 (0 à 1)")
    EXT_SOURCE_3: float = Field(None, ge=0, le=1, description="Score externe 3 (0 à 1)")

    class Config:
        json_schema_extra = {
            "example": {
                "AGE_ANNEES": 42, "CODE_GENDER": "M",
                "NAME_FAMILY_STATUS": "Married", "CNT_CHILDREN": 1,
                "CNT_FAM_MEMBERS": 3,
                "NAME_EDUCATION_TYPE": "Secondary / secondary special",
                "OCCUPATION_TYPE": "Laborers", "ORGANIZATION_TYPE": "Government",
                "NAME_INCOME_TYPE": "Working", "ANCIENNETE_EMPLOI_ANNEES": 5,
                "EMPLOI_ANORMAL": 0, "AMT_INCOME_TOTAL": 450000,
                "AMT_CREDIT": 2500000, "AMT_ANNUITY": 75000,
                "AMT_GOODS_PRICE": 2400000, "NAME_CONTRACT_TYPE": "Cash loans",
                "EXT_SOURCE_1": 0.5, "EXT_SOURCE_2": 0.6, "EXT_SOURCE_3": 0.55
            }
        }


class FacteurExplication(BaseModel):
    """Un facteur explicatif issu de l'analyse SHAP."""
    variable: str = Field(..., description="Nom de la variable")
    contribution: float = Field(..., description="Contribution au risque (positif = augmente, négatif = diminue)")


class ResultatAnalyse(BaseModel):
    """Résultat renvoyé par l'API après analyse d'un dossier."""
    probabilite_defaut: float = Field(..., description="Probabilité de défaut estimée (0 à 1)")
    classe_risque: str = Field(..., description="Classe de risque : faible, moyen, élevé")
    decision: str = Field(..., description="Recommandation : ACCORDE ou REFUSE")
    seuil_utilise: float = Field(..., description="Seuil de décision appliqué")
    facteurs_explicatifs: list[FacteurExplication] = Field(
        ..., description="Principaux facteurs ayant influencé la décision (SHAP)")
    explication: str = Field(
        "", description="Explication de la décision en langage naturel")
# -*- coding: utf-8 -*-
"""
Tests automatiques du service de modelisation.

Ces tests verifient que le modele charge bien et produit des predictions
coherentes. Ils ne necessitent ni base de donnees ni cle API externe.
"""

import os
import sys
import pytest

# Permettre l'import du package app depuis la racine du projet
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# Dossier de test : un dossier de credit type
DOSSIER_TEST = {
    "AGE_ANNEES": 42, "CODE_GENDER": "M", "NAME_FAMILY_STATUS": "Married",
    "CNT_CHILDREN": 1, "CNT_FAM_MEMBERS": 3,
    "NAME_EDUCATION_TYPE": "Secondary / secondary special",
    "OCCUPATION_TYPE": "Laborers", "ORGANIZATION_TYPE": "Government",
    "NAME_INCOME_TYPE": "Working", "ANCIENNETE_EMPLOI_ANNEES": 5,
    "EMPLOI_ANORMAL": 0, "AMT_INCOME_TOTAL": 450000, "AMT_CREDIT": 2500000,
    "AMT_ANNUITY": 75000, "AMT_GOODS_PRICE": 2400000,
    "NAME_CONTRACT_TYPE": "Cash loans",
    "EXT_SOURCE_1": 0.5, "EXT_SOURCE_2": 0.6, "EXT_SOURCE_3": 0.55,
}


@pytest.fixture(scope="module")
def service():
    """Charge le service de modelisation une fois pour tous les tests."""
    from app.model_service import ServiceModele
    return ServiceModele()


def test_modele_se_charge(service):
    """Le modele doit se charger sans erreur."""
    assert service.pipeline is not None
    assert service.classifieur is not None


def test_prediction_dans_intervalle(service):
    """La probabilite de defaut doit etre comprise entre 0 et 1."""
    proba = service.predire(DOSSIER_TEST)
    assert 0.0 <= proba <= 1.0


def test_analyse_complete(service):
    """L'analyse complete doit renvoyer tous les champs attendus."""
    resultat = service.analyser(DOSSIER_TEST)
    assert "probabilite_defaut" in resultat
    assert "decision" in resultat
    assert resultat["decision"] in ("ACCORDE", "REFUSE")
    assert "classe_risque" in resultat
    assert "facteurs_explicatifs" in resultat
    assert "explication" in resultat
    # L'explication ne doit pas etre vide
    assert len(resultat["explication"]) > 10


def test_facteurs_explicatifs(service):
    """L'analyse doit renvoyer des facteurs explicatifs (SHAP)."""
    resultat = service.analyser(DOSSIER_TEST)
    facteurs = resultat["facteurs_explicatifs"]
    assert isinstance(facteurs, list)
    assert len(facteurs) > 0
    # Chaque facteur a un nom et une contribution
    for f in facteurs:
        assert "variable" in f
        assert "contribution" in f
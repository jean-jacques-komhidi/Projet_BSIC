# -*- coding: utf-8 -*-
"""
Tests de la fiche de decision PDF.
"""

import os
import sys
import json
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.pdf_service import (
    generer_pdf_decision, code_authenticite, _facteurs_affiches, _ratios,
    _conditions_ou_recommandations,
)

DOSSIER = {"AMT_INCOME_TOTAL": 120000, "AMT_ANNUITY": 420000, "AMT_CREDIT": 9000000,
           "AMT_GOODS_PRICE": 8800000, "NAME_CONTRACT_TYPE": "Cash loans",
           "EXT_SOURCE_3": 0.12, "AGE_ANNEES": 24}
FACTEURS = [{"variable": "EXT_SOURCE_3", "contribution": 0.5},
            {"variable": "CODE_GENDER_F", "contribution": 0.2},
            {"variable": "AGE_ANNEES", "contribution": -0.1}]


def _analyse(**kw):
    a = dict(id=57, decision="REFUSE", classe_risque="eleve", probabilite_defaut=0.86,
             explication="", facteurs_explicatifs=json.dumps(FACTEURS),
             donnees_dossier=json.dumps(DOSSIER), date_analyse=datetime(2026, 10, 15, 14, 30),
             version_modele=None)
    a.update(kw)
    return SimpleNamespace(**a)


def test_la_fiche_est_un_pdf():
    client = SimpleNamespace(nom="Client Test", genre="F", age=24, profession="Commerçante",
                             situation_familiale="Single / not married")
    pdf = generer_pdf_decision(_analyse(), client, "Agent Test")
    assert pdf.startswith(b"%PDF") and len(pdf) > 5000


def test_le_genre_n_est_jamais_un_facteur_affiche():
    libelles = [f["libelle"] for f in _facteurs_affiches(_analyse(), DOSSIER)]
    assert "Genre" not in libelles
    assert libelles == ["Note de solvabilité externe 3", "Âge"]


def test_code_authenticite_change_si_la_decision_change():
    assert code_authenticite(_analyse()) != code_authenticite(_analyse(decision="ACCORDE"))
    assert code_authenticite(_analyse()) == code_authenticite(_analyse())


def test_recommandations_adaptees_au_dossier():
    ratios = _ratios(DOSSIER)
    assert round(ratios["endettement"], 2) == 3.5
    facteurs = _facteurs_affiches(_analyse(), DOSSIER)
    titre, lignes = _conditions_ou_recommandations(False, facteurs, ratios)
    assert titre.startswith("RECOMMANDATIONS")
    assert "350 %" in lignes[0]

# -*- coding: utf-8 -*-
"""
Tests de l'explication en langage naturel.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.explication import generer_explication


def test_explication_accorde():
    """Pour un credit accorde, l'explication doit mentionner l'accord."""
    facteurs = [
        {"variable": "EXT_SOURCE_3", "contribution": -0.3},
        {"variable": "AMT_CREDIT", "contribution": 0.1},
    ]
    texte = generer_explication("ACCORDE", facteurs)
    assert "accorde" in texte.lower()
    assert len(texte) > 20


def test_explication_refuse_avec_conseils():
    """Pour un refus, l'explication doit proposer des ameliorations."""
    facteurs = [
        {"variable": "AMT_CREDIT", "contribution": 0.4},
        {"variable": "EXT_SOURCE_2", "contribution": 0.3},
    ]
    texte = generer_explication("REFUSE", facteurs)
    assert "refuse" in texte.lower()
    # Doit contenir des conseils d'amelioration
    assert "ameliorer" in texte.lower() or "reduire" in texte.lower()
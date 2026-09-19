# -*- coding: utf-8 -*-
"""
Tests de la securite (hachage des mots de passe).
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.security import hacher_mot_de_passe, verifier_mot_de_passe


def test_hachage_different_du_clair():
    """Le mot de passe hache ne doit pas etre en clair."""
    mdp = "motdepasse123"
    empreinte = hacher_mot_de_passe(mdp)
    assert empreinte != mdp
    assert len(empreinte) > 20


def test_verification_correcte():
    """Un mot de passe correct doit etre reconnu."""
    mdp = "motdepasse123"
    empreinte = hacher_mot_de_passe(mdp)
    assert verifier_mot_de_passe(mdp, empreinte) is True


def test_verification_incorrecte():
    """Un mauvais mot de passe doit etre rejete."""
    empreinte = hacher_mot_de_passe("bonmotdepasse")
    assert verifier_mot_de_passe("mauvais", empreinte) is False
# -*- coding: utf-8 -*-
"""
Configuration de la journalisation (logging) de l'API CREDISCORE.

La journalisation enregistre ce qui se passe dans l'application : les analyses
realisees, les connexions, et surtout les erreurs. Ces traces sont ecrites a
la fois dans la console et dans un fichier (logs/crediscore.log), ce qui
facilite le suivi et le debogage.
"""

import logging
import os

# Dossier des journaux
DOSSIER_LOGS = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(DOSSIER_LOGS, exist_ok=True)
FICHIER_LOG = os.path.join(DOSSIER_LOGS, "crediscore.log")


def configurer_logging():
    """Configure le systeme de journalisation de l'application."""
    logger = logging.getLogger("crediscore")
    logger.setLevel(logging.INFO)

    # Eviter d'ajouter les handlers plusieurs fois (rechargement)
    if logger.handlers:
        return logger

    format_log = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Sortie console
    console = logging.StreamHandler()
    console.setFormatter(format_log)
    logger.addHandler(console)

    # Sortie fichier
    fichier = logging.FileHandler(FICHIER_LOG, encoding="utf-8")
    fichier.setFormatter(format_log)
    logger.addHandler(fichier)

    return logger


# Instance du logger, utilisable dans toute l'application
logger = configurer_logging()
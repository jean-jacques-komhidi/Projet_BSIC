# -*- coding: utf-8 -*-
"""
Gestion centralisee des erreurs de l'API CREDISCORE.

Ce module definit des gestionnaires d'erreurs qui capturent les exceptions et
renvoient des reponses claires et coherentes, au lieu d'exposer des messages
techniques bruts. Toutes les erreurs sont enregistrees dans le journal.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from .logging_config import logger


def enregistrer_gestionnaires(app):
    """Enregistre les gestionnaires d'erreurs sur l'application FastAPI."""

    # --- Erreurs de validation des donnees (Pydantic) ---
    @app.exception_handler(RequestValidationError)
    async def erreur_validation(request: Request, exc: RequestValidationError):
        logger.warning(f"Donnees invalides sur {request.url.path} : {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "erreur": "Donnees invalides",
                "detail": "Certains champs sont manquants ou incorrects.",
                "champs": [
                    {"champ": " > ".join(str(x) for x in e["loc"]), "probleme": e["msg"]}
                    for e in exc.errors()
                ],
            },
        )

    # --- Erreurs de base de donnees ---
    @app.exception_handler(SQLAlchemyError)
    async def erreur_bdd(request: Request, exc: SQLAlchemyError):
        logger.error(f"Erreur base de donnees sur {request.url.path} : {exc}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "erreur": "Service indisponible",
                "detail": "Un probleme est survenu avec la base de donnees. "
                          "Veuillez reessayer dans un instant.",
            },
        )

    # --- Toute autre erreur inattendue ---
    @app.exception_handler(Exception)
    async def erreur_generique(request: Request, exc: Exception):
        logger.error(f"Erreur inattendue sur {request.url.path} : {type(exc).__name__} : {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "erreur": "Erreur interne",
                "detail": "Une erreur inattendue est survenue. "
                          "L'incident a ete enregistre.",
            },
        )
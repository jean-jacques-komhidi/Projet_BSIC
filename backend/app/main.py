# -*- coding: utf-8 -*-
"""
API CREDISCORE - Point d'entree.

Routes principales :
- GET  /            : verifier que l'API fonctionne
- POST /analyser    : simuler une analyse (libre)
- /auth/...         : authentification et utilisateurs
- /clients/...      : gestion des clients
- /analyses/...     : analyses enregistrees + export PDF
- /reentrainer      : reentrainement du modele (admin)
- /chatbot          : assistant conversationnel
- /dashboard        : tableau de bord
- /drift            : surveillance de la derive (admin)

Pour la lancer : uvicorn app.main:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import DossierCredit, ResultatAnalyse
from .model_service import ServiceModele
from .logging_config import logger
from .erreurs import enregistrer_gestionnaires
from . import auth_routes, client_routes, analyse_routes
from . import reentrainement_routes, chatbot_routes, dashboard_routes, drift_routes

app = FastAPI(
    title="API CREDISCORE - BSIC Tchad",
    description="Service de scoring du risque de defaut de paiement de credit.",
    version="1.7.0",
)

# --- Gestion centralisee des erreurs ---
enregistrer_gestionnaires(app)

# --- CORS : autorise l'interface (frontend) a communiquer avec l'API ---
origines_autorisees = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:5173", "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origines_autorisees,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
app.include_router(auth_routes.router)
app.include_router(client_routes.router)
app.include_router(analyse_routes.router)
app.include_router(reentrainement_routes.router)
app.include_router(chatbot_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(drift_routes.router)

# --- Chargement du modele au demarrage (avec gestion d'erreur) ---
service = None
try:
    service = ServiceModele()
    logger.info("Modele charge avec succes au demarrage.")
except Exception as e:
    logger.error(f"Impossible de charger le modele au demarrage : {e}")
    # L'API demarre quand meme ; la route /analyser signalera l'indisponibilite.


@app.on_event("startup")
def au_demarrage():
    logger.info("API CREDISCORE demarree (version 1.7.0).")


@app.get("/")
def accueil():
    """Route de verification : confirme que l'API est en ligne."""
    return {
        "message": "API CREDISCORE operationnelle",
        "version": "1.7.0",
        "modele_charge": service is not None,
    }


@app.post("/analyser", response_model=ResultatAnalyse)
def analyser_dossier(dossier: DossierCredit):
    """Simule une analyse de credit (sans enregistrement)."""
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Le modele de scoring est indisponible. Contactez l'administrateur.")
    resultat = service.analyser(dossier.model_dump())
    logger.info(f"Analyse simulee : decision={resultat['decision']}, "
                f"proba={resultat['probabilite_defaut']}")
    return resultat
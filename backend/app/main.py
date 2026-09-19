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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .schemas import DossierCredit, ResultatAnalyse
from .model_service import ServiceModele
from . import auth_routes
from . import client_routes
from . import analyse_routes
from . import reentrainement_routes
from . import chatbot_routes
from . import dashboard_routes
from . import drift_routes

app = FastAPI(
    title="API CREDISCORE - BSIC Tchad",
    description="Service de scoring du risque de defaut de paiement de credit.",
    version="1.6.0",
)

# --- CORS : autorise l'interface (frontend) a communiquer avec l'API ---
# En developpement, on autorise les adresses locales habituelles de React.
# En production, remplacer par l'adresse reelle du frontend.
origines_autorisees = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",   # Vite (autre outil React courant)
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origines_autorisees,
    allow_credentials=True,
    allow_methods=["*"],       # autorise toutes les methodes (GET, POST, etc.)
    allow_headers=["*"],       # autorise tous les en-tetes (dont le jeton)
)

# --- Routes ---
app.include_router(auth_routes.router)
app.include_router(client_routes.router)
app.include_router(analyse_routes.router)
app.include_router(reentrainement_routes.router)
app.include_router(chatbot_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(drift_routes.router)

service = ServiceModele()


@app.get("/")
def accueil():
    return {"message": "API CREDISCORE operationnelle", "version": "1.6.0"}


@app.post("/analyser", response_model=ResultatAnalyse)
def analyser_dossier(dossier: DossierCredit):
    """Simule une analyse de credit (sans enregistrement)."""
    resultat = service.analyser(dossier.model_dump())
    return resultat
# Backend — API CREDISCORE

API FastAPI de CREDISCORE : scoring, explication SHAP, CrediBot, surveillance et réentraînement du modèle. La présentation générale du projet est dans le [README principal](../README.md).

## Démarrer

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows  (Linux/Mac : source venv/bin/activate)
pip install -r requirements.txt
copy .env.exemple .env         # puis remplissez .env  (Linux/Mac : cp)
python -m app.init_db
python -m app.creer_admin
uvicorn app.main:app --reload --port 8000
```

Documentation interactive : http://localhost:8000/docs

## Configuration (`.env`)

| Variable | Rôle |
|----------|------|
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME` | Base PostgreSQL locale (ou `DATABASE_URL` complète) |
| `SECRET_KEY` | Signature des jetons de connexion (longue et aléatoire) |
| `GROQ_API_KEY` | Clé de l'API Groq pour CrediBot |
| `ADMIN_NOM`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Premier administrateur, créé par `python -m app.creer_admin` |
| `MOT_DE_PASSE_AGENTS` | Mot de passe des agents de démonstration |
| `CORS_ORIGINS`, `FRONTEND_URL` | En production : adresse de l'interface (CORS et QR code des fiches PDF) |

Le fichier `.env` n'est jamais publié (voir `.gitignore`).

## Scripts

| Commande | Effet |
|----------|-------|
| `python -m app.init_db` | Crée les tables et ajoute les colonnes manquantes (sans effacer de données) |
| `python -m app.creer_admin` | Crée le premier administrateur s'il n'en existe aucun |
| `python -m app.generer_donnees_test` | Données de démonstration : 18 mois d'analyses, issues réelles, dérive progressive |
| `python notebook/04_entrainement_mlflow.py` | Entraînement initial des trois modèles, suivi dans MLflow |

## Organisation

| Fichier | Rôle |
|---------|------|
| `main.py` | Application, CORS, enregistrement des routes |
| `models.py`, `database.py`, `init_db.py` | Tables SQLAlchemy et mises à jour du schéma |
| `security.py` | Hachage bcrypt, jetons JWT, règles de mot de passe, rôles |
| `model_service.py`, `explication.py` | Prédiction, SHAP, explication en langage clair |
| `surveillance_service.py`, `alertes_service.py` | PSI, performance réelle, règle de réentraînement, notifications |
| `reentrainement.py`, `retrain_manager.py` | Réentraînement en tâche de fond, champion / challenger |
| `chatbot_service.py` | Contexte de CrediBot, pseudonymisation, appel à Groq |
| `pdf_service.py` | Fiche de décision avec QR code |
| `export_service.py` | Export CSV / Excel et dictionnaire des données |
| `*_routes.py` | Routes par domaine (auth, clients, analyses, dashboard, recherche, conversations, notifications, monitoring, reentrainer, export) |

## Tests

```bash
pytest tests/ -q
```

90 tests sur une base SQLite temporaire : aucun ne touche à la base PostgreSQL. Pour le CI, `requirements-ci.txt` installe une version allégée des dépendances.

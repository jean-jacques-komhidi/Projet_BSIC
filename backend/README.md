# CREDISCORE-BSIC — Scoring Crédit avec Machine Learning

**Système de prédiction du risque de défaut de paiement de crédit bancaire au Tchad**

Application complète de scoring crédit développée dans le cadre d'un mémoire de master. Le projet couvre l'ensemble de la chaîne : préparation des données, entraînement et comparaison de modèles de Machine Learning, API de prédiction, explicabilité des décisions (SHAP), assistant conversationnel (LLM), réentraînement avec suivi MLflow et surveillance de la dérive des données. Cas d'application : la Banque Sahélo-Saharienne pour l'Investissement et le Commerce (BSIC Tchad).

---

## Table des matières

- [Contexte](#contexte)
- [Jeu de données](#jeu-de-données)
- [Pile technique](#pile-technique)
- [Fonctionnalités](#fonctionnalités)
- [Architecture technique](#architecture-technique)
- [Structure du projet](#structure-du-projet)
- [Résultats des modèles](#résultats-des-modèles)
- [Score métier](#score-métier)
- [Réentraînement](#réentraînement)
- [Surveillance de la dérive (Data Drift)](#surveillance-de-la-dérive-data-drift)
- [Assistant conversationnel](#assistant-conversationnel)
- [Installation](#installation)
- [Accès aux services](#accès-aux-services)
- [Auteur](#auteur)

---

## Contexte

| Élément        | Détail                                                                 |
| -------------- | ---------------------------------------------------------------------- |
| Nature         | Mémoire de master — scoring crédit bancaire                            |
| Objectif       | Prédire le risque de défaut de paiement d'un demandeur de crédit       |
| Terrain        | BSIC Tchad (secteur bancaire tchadien)                                 |
| Périmètre      | Données → modélisation → API → explicabilité → chatbot → monitoring    |
| Modèle retenu  | Gradient Boosting (AUC = 0,753)                                        |

Le secteur bancaire tchadien se caractérise par une faible bancarisation et un taux élevé de créances en souffrance. Ce projet propose une approche de scoring fondée sur l'apprentissage automatique, tout en respectant les exigences d'explicabilité du régulateur (COBAC), afin d'aider les agents de crédit à évaluer le risque de défaut de manière objective et traçable.

---

## Jeu de données

**Home Credit Default Risk** (Kaggle), utilisé comme base de substitution en l'absence d'accès aux données réelles de la BSIC (secret bancaire).

| Caractéristique          | Valeur                                                   |
| ------------------------ | -------------------------------------------------------- |
| Dossiers                 | 307 511                                                  |
| Variables retenues       | 18 (correspondant à la fiche de prêt de la BSIC)        |
| Cible                    | `TARGET` binaire (1 = défaut, 0 = sain)                 |
| Déséquilibre des classes | 91,9 % sains / 8,1 % en défaut                          |

Les variables ont été sélectionnées pour correspondre aux informations réellement collectées par la BSIC. Le déséquilibre est traité par pondération des classes.

---

## Pile technique

| Couche               | Technologies                                                       |
| -------------------- | ----------------------------------------------------------------- |
| API                  | FastAPI, Uvicorn, Python 3.11                                     |
| Machine Learning     | scikit-learn, LightGBM, LogisticRegression, RandomForest          |
| Explicabilité        | SHAP                                                               |
| Suivi des modèles    | MLflow (tracking, versioning)                                     |
| Base de données      | PostgreSQL                                                         |
| Assistant (LLM)      | Groq (API gratuite), LangChain                                   |
| Génération PDF       | ReportLab                                                         |
| Surveillance         | PSI (Population Stability Index)                                  |
| Frontend             | React (à venir)                                                   |

---

## Fonctionnalités

| Fonctionnalité              | Description                                                            | Accès          |
| --------------------------- | --------------------------------------------------------------------- | -------------- |
| Analyse de crédit           | Calcul du score, décision et explication SHAP                        | Agent, Admin   |
| Explication en langage clair| Traduction des facteurs SHAP en texte, avec conseils si refus         | Agent, Admin   |
| Gestion des clients (CRUD)  | Création, consultation, modification des demandeurs                    | Agent, Admin   |
| Historique des analyses     | Traçabilité complète (client, agent, modèle, score)                   | Agent, Admin   |
| Export PDF                  | Fiche de décision imprimable pour le dossier physique                 | Agent, Admin   |
| Assistant conversationnel   | Questions en langage naturel (statistiques + explication de dossier)  | Agent, Admin   |
| Tableau de bord             | Statistiques agrégées et activité récente                            | Agent, Admin   |
| Gestion des utilisateurs    | CRUD des comptes et rôles                                            | Admin          |
| Réentraînement              | Relance multi-modèles, sélection du meilleur, versioning MLflow       | Admin          |
| Surveillance (Data Drift)   | Détection de la dérive des données (PSI)                              | Admin          |

---

## Architecture technique

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND (React)                  │
│   Tableau de bord | Analyse | Clients | Assistant   │
│   Historique | Monitoring | Utilisateurs            │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP (Axios)
                      ▼
┌─────────────────────────────────────────────────────┐
│                 BACKEND (FastAPI, port 8000)         │
│   /analyses | /clients | /auth | /chatbot           │
│   /dashboard | /reentrainer | /drift                │
│   Authentification JWT + rôles (agent/admin)        │
└──────────┬───────────────────────┬──────────────────┘
           │                       │
           ▼                       ▼
┌────────────────────┐    ┌────────────────────────┐
│   Service ML       │    │      PostgreSQL         │
│   Modèle + SHAP    │    │   credit_bsic           │
│   Explication      │    │   - users               │
└────────────────────┘    │   - clients             │
                          │   - analyses            │
┌────────────────────┐    │   - model_versions      │
│   MLflow (port 5000)│    └────────────────────────┘
│   Suivi + versioning│
└────────────────────┘
┌────────────────────┐
│   Groq (LLM)        │    Service externe (Internet)
│   Assistant         │
└────────────────────┘
```

---

## Structure du projet

```
backend/
├── app/
│   ├── main.py                  # Point d'entrée de l'API
│   ├── database.py              # Connexion PostgreSQL
│   ├── models.py                # Tables (users, clients, analyses, model_versions)
│   ├── security.py              # Authentification JWT et rôles
│   ├── model_service.py         # Chargement du modèle, prédiction, SHAP
│   ├── explication.py           # Explication en langage naturel
│   ├── pdf_service.py           # Génération de la fiche PDF
│   ├── chatbot_service.py       # Assistant conversationnel (Groq + LangChain)
│   ├── reentrainement.py        # Réentraînement multi-modèles
│   ├── drift_service.py         # Surveillance de la dérive (PSI)
│   ├── auth_routes.py           # Routes authentification et utilisateurs
│   ├── client_routes.py         # Routes clients
│   ├── analyse_routes.py        # Routes analyses + export PDF
│   ├── chatbot_routes.py        # Route assistant
│   ├── dashboard_routes.py      # Route tableau de bord
│   ├── reentrainement_routes.py # Route réentraînement
│   ├── drift_routes.py          # Route surveillance
│   └── logo_bsic.png            # Logo pour les PDF
├── models/
│   └── modele_credistore.pkl    # Modèle en production
├── notebook/
│   ├── CREDISCORE_pipeline.ipynb # Notebook d'exploration et d'entraînement
│   ├── 04_entrainement_mlflow.py # Entraînement avec suivi MLflow
│   └── application_train.csv     # Jeu de données
├── mlflow/                       # Artefacts MLflow
├── .env                          # Variables d'environnement (non versionné)
├── requirements.txt
└── README.md
```

---

## Résultats des modèles

Trois modèles sont entraînés et comparés. Le meilleur est sélectionné et déployé.

| Modèle               | AUC (test) | Coût métier |
| -------------------- | ---------- | ----------- |
| Régression logistique| 0,740      | 21 446      |
| Random Forest        | 0,737      | 21 997      |
| **Gradient Boosting**| **0,753**  | **20 868**  |

Le Gradient Boosting obtient la meilleure performance, à la fois en AUC et en coût métier.

---

## Score métier

Les deux types d'erreurs n'ont pas le même coût pour la banque :

| Erreur            | Signification                          | Coût |
| ----------------- | -------------------------------------- | ---- |
| Faux négatif (FN) | Accorder un crédit à un futur défaut   | 5    |
| Faux positif (FP) | Refuser un bon client                  | 1    |

**Formule** : `Coût = (5 × FN) + (1 × FP)` — à minimiser.

**Seuil de décision** : 0,70, choisi pour minimiser le coût métier, un défaut coûtant cinq fois plus cher qu'un bon client refusé.

---

## Réentraînement

```
Données socle (application_train)
         +
Analyses réelles résolues (résultat connu : remboursé / défaut)
                    |
         Préparation + pondération des classes
                    |
    Régression logistique | Random Forest | Gradient Boosting
                    |
       Comparaison AUC + coût métier
                    |
      Meilleur modèle → modele_credistore.pkl
                    |
     Nouvelle version en base + marquée en production
                    |
             Enregistrement dans MLflow
```

Le réentraînement combine le socle historique et les analyses réelles dont l'issue est connue, ce qui permet au modèle de s'améliorer au fil du temps.

---

## Surveillance de la dérive (Data Drift)

La dérive est mesurée par le PSI (Population Stability Index), qui compare la distribution des données récentes à celle des données d'entraînement.

| PSI          | Statut            | Action                      |
| ------------ | ----------------- | --------------------------- |
| < 0,10       | Stable            | Aucune action               |
| 0,10 à 0,25  | Dérive modérée    | À surveiller                |
| > 0,25       | Dérive importante | Réentraînement recommandé   |

---

## Assistant conversationnel

L'assistant répond aux questions de l'agent en langage naturel, selon deux mécanismes :

- **Questions sur les données** (statistiques) : un résumé de la base est fourni au modèle de langage, qui formule la réponse.
- **Questions sur un dossier** (RAG) : le contexte de l'analyse (score, facteurs) est fourni au modèle, qui explique la décision.

Le modèle de langage est appelé via l'API gratuite de Groq, orchestré par LangChain.

---

## Installation

### Prérequis

- Python 3.11
- PostgreSQL
- Une clé API Groq (gratuite, sur console.groq.com)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows
source venv/bin/activate         # Linux/Mac

pip install -r requirements.txt

# Créer la base
psql -U postgres -c "CREATE DATABASE credit_bsic;"

# Configurer le fichier .env (voir .env.exemple)

# Créer les tables
python -m app.init_db

# Terminal 1 — MLflow
mlflow server --backend-store-uri postgresql://postgres:MOT_DE_PASSE@localhost:5432/mlflow_bsic --default-artifact-root ./mlflow/artifacts --host 127.0.0.1 --port 5000

# Terminal 2 — API
uvicorn app.main:app --reload --port 8000
```

### Variables d'environnement (`.env`)

```
DB_USER=postgres
DB_PASSWORD=votre_mot_de_passe
DB_HOST=localhost
DB_PORT=5432
DB_NAME=credit_bsic
SECRET_KEY=votre_cle_secrete
GROQ_API_KEY=votre_cle_groq
```

---

## Accès aux services

| Service                     | URL                          |
| --------------------------- | ---------------------------- |
| API FastAPI                 | http://localhost:8000        |
| Documentation API (Swagger) | http://localhost:8000/docs   |
| MLflow                      | http://localhost:5000        |
| Frontend React              | http://localhost:5173 (à venir) |

---

## Auteur

**Mémoire de master** — Modélisation prédictive du risque de défaut de paiement de crédit dans le secteur bancaire tchadien : apport du Machine Learning au scoring crédit, cas de la BSIC Tchad.

---

## Licence

Projet académique — usage pédagogique et démonstratif.
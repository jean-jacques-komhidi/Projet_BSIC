# CREDISCORE-BSIC — Scoring Crédit avec Machine Learning

**Système complet de prédiction du risque de défaut de paiement de crédit bancaire au Tchad**

Application full-stack de scoring crédit développée dans le cadre d'un mémoire de master. Le projet couvre l'ensemble de la chaîne : préparation des données, entraînement et comparaison de modèles de Machine Learning, API de prédiction, explicabilité des décisions (SHAP), assistant conversationnel (LLM avec mémoire), réentraînement asynchrone avec suivi MLflow, surveillance de la dérive des données, et une interface web complète. Cas d'application : la Banque Sahélo-Saharienne pour l'Investissement et le Commerce (BSIC Tchad).

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
- [Interface web](#interface-web)
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
| Périmètre      | Données → modélisation → API → explicabilité → chatbot → monitoring → interface |
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
| Interface (frontend) | React, Vite, Tailwind CSS, Chart.js, Lucide, React Markdown       |
| API (backend)        | FastAPI, Uvicorn, Python 3.11                                     |
| Machine Learning     | scikit-learn, LightGBM, LogisticRegression, RandomForest          |
| Explicabilité        | SHAP                                                               |
| Suivi des modèles    | MLflow (tracking, versioning)                                     |
| Base de données      | PostgreSQL                                                         |
| Assistant (LLM)      | Groq (API gratuite), LangChain                                   |
| Génération PDF       | ReportLab                                                         |
| Surveillance         | PSI (Population Stability Index) et z-score                       |

---

## Fonctionnalités

| Fonctionnalité              | Description                                                            | Accès          |
| --------------------------- | --------------------------------------------------------------------- | -------------- |
| Analyse de crédit           | Calcul du score, décision, jauge de risque et explication SHAP        | Agent, Admin   |
| Explication en langage clair| Traduction des facteurs SHAP en texte, avec conseils si refus         | Agent, Admin   |
| Gestion des clients (CRUD)  | Création, consultation, modification, recherche des demandeurs        | Agent, Admin   |
| Historique des analyses     | Traçabilité complète, filtres, recherche, page de détail dédiée       | Agent, Admin   |
| Export PDF                  | Fiche de décision imprimable pour le dossier physique                 | Agent, Admin   |
| Résultat réel               | Renseigner l'issue du crédit (remboursé / défaut) pour le réentraînement | Admin       |
| Assistant conversationnel   | CrediBot : questions en langage naturel, mémoire, historique des conversations | Agent, Admin |
| Notifications               | Événements de l'application (réentraînement, dérive), badge de non-lues | Agent, Admin |
| Tableau de bord             | KPI, graphiques animés, activité récente                             | Agent, Admin   |
| Profil                      | Informations, statistiques d'activité, changement de mot de passe     | Agent, Admin   |
| Gestion des utilisateurs    | CRUD des comptes et rôles (pages dédiées)                            | Admin          |
| Monitoring                  | Suivi MLflow, réentraînement en temps réel, data drift détaillé       | Admin          |

---

## Architecture technique

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                   │
│   Connexion | Tableau de bord | Analyse | Détail            │
│   Clients | Historique | Assistant IA | Notifications       │
│   Utilisateurs | Monitoring | Profil                        │
│   Thème clair/sombre · Sidebar par rôle                     │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (Axios) + JWT
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI, port 8000)                │
│   /auth · /clients · /analyses · /conversations             │
│   /notifications · /dashboard · /monitoring · /drift        │
│   Authentification JWT + rôles (agent/admin)                │
│   Gestion d'erreurs centralisée · Journalisation            │
└──────────┬─────────────────┬──────────────────┬─────────────┘
           │                 │                  │
           ▼                 ▼                  ▼
┌────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Service ML    │  │    PostgreSQL     │  │  Service ML/Ops  │
│  Modèle + SHAP │  │  credit_bsic      │  │  Réentraînement  │
│  Explication   │  │  - users          │  │  asynchrone      │
└────────────────┘  │  - clients        │  │  Drift (PSI/z)   │
                    │  - analyses       │  └────────┬─────────┘
┌────────────────┐  │  - model_versions │           ▼
│  Groq (LLM)    │  │  - notifications  │  ┌──────────────────┐
│  CrediBot      │  │  - conversations  │  │ MLflow (port 5000)│
│  (RAG + stats) │  │  - messages       │  │ Suivi + versioning│
└────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## Structure du projet

```
Projet_BSIC/
├── .github/workflows/ci.yml       # Intégration continue (tests automatiques)
├── backend/
│   ├── app/
│   │   ├── main.py                 # Point d'entrée de l'API
│   │   ├── database.py             # Connexion PostgreSQL
│   │   ├── models.py               # Tables (users, clients, analyses, model_versions,
│   │   │                           #         notifications, conversations, messages)
│   │   ├── security.py             # Authentification JWT et rôles
│   │   ├── logging_config.py       # Journalisation
│   │   ├── erreurs.py              # Gestion centralisée des erreurs
│   │   ├── model_service.py        # Chargement du modèle, prédiction, SHAP
│   │   ├── explication.py          # Explication en langage naturel
│   │   ├── pdf_service.py          # Génération de la fiche PDF
│   │   ├── chatbot_service.py      # Assistant CrediBot (Groq + contexte)
│   │   ├── reentrainement.py       # Réentraînement multi-modèles
│   │   ├── retrain_manager.py      # Réentraînement asynchrone (progression)
│   │   ├── monitoring_service.py   # Lecture des runs MLflow
│   │   ├── drift_service.py        # Surveillance de la dérive (PSI, z-score)
│   │   ├── notification_service.py # Création des notifications
│   │   ├── generer_donnees_test.py # Génération de données de démonstration
│   │   ├── auth_routes.py          # Auth, utilisateurs, profil, statistiques
│   │   ├── client_routes.py        # Clients (CRUD + recherche)
│   │   ├── analyse_routes.py       # Analyses + export PDF + résultat réel
│   │   ├── chatbot_routes.py       # Assistant (question simple)
│   │   ├── conversation_routes.py  # Conversations (mémoire, historique)
│   │   ├── notification_routes.py  # Notifications
│   │   ├── dashboard_routes.py     # Tableau de bord
│   │   ├── monitoring_routes.py    # Monitoring (MLflow, retrain, drift)
│   │   ├── drift_routes.py         # Surveillance
│   │   └── logo_bsic.png           # Logo pour les PDF
│   ├── tests/                      # Tests automatiques (modèle, explication, sécurité)
│   ├── models/modele_credistore.pkl
│   ├── notebook/                   # Notebook, script MLflow, jeu de données
│   ├── requirements.txt
│   └── requirements-ci.txt         # Dépendances allégées pour le CI
└── frontend/
    ├── src/
    │   ├── pages/                  # Login, Dashboard, Analyse, Détail, Clients,
    │   │                           # Historique, Assistant, Notifications,
    │   │                           # Utilisateurs, Monitoring, Profil
    │   ├── components/             # Sidebar, Header, ScoreForm, ScoreResult,
    │   │                           # ShapChart, JaugeScore, MetricCard
    │   ├── context/                # Auth, Theme, Notifications
    │   └── services/               # Appels API (axios)
    └── package.json
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

Le réentraînement s'exécute de manière **asynchrone** (en tâche de fond), avec un suivi de progression en temps réel affiché dans l'interface de monitoring.

```
Données socle (application_train)
         +
Analyses réelles résolues (résultat renseigné : remboursé / défaut)
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

Le réentraînement combine le socle historique et les analyses réelles dont l'issue est connue (renseignée depuis la page de détail d'une analyse), ce qui permet au modèle de s'améliorer au fil du temps. C'est la boucle MLOps complète.

---

## Surveillance de la dérive (Data Drift)

Pour chaque variable surveillée, la distribution des données de production (analyses récentes) est comparée à celle des données de référence (socle d'entraînement). L'application calcule, par variable : l'écart en pourcentage, le z-score, les moyennes de référence et de production, et un statut.

| Z-score      | Statut     | Interprétation           |
| ------------ | ---------- | ------------------------ |
| ≤ 1          | NORMAL     | Distribution stable      |
| 1 à 2        | ALERTE     | Dérive modérée           |
| > 2          | CRITIQUE   | Dérive significative     |

Un indice PSI (Population Stability Index) complète cette analyse. Une dérive importante déclenche une notification recommandant un réentraînement.

---

## Assistant conversationnel

**CrediBot** répond aux questions de l'agent en langage naturel, avec deux mécanismes :

- **Questions sur les données** : un résumé statistique et la liste des clients (avec leur dernière analyse) sont fournis au modèle de langage, qui formule la réponse.
- **Questions sur un dossier** (RAG) : le contexte d'une analyse précise (score, décision, facteurs) est fourni au modèle, qui explique la décision et propose des pistes d'amélioration.

L'assistant dispose d'une **mémoire conversationnelle** (il tient compte des messages précédents) et d'un **historique des conversations** sauvegardé en base, groupé par date. Les réponses sont mises en forme (Markdown : tableaux, listes). Le modèle de langage est appelé via l'API gratuite de Groq.

---

## Interface web

L'interface React couvre l'ensemble des fonctionnalités, avec un thème clair/sombre, une navigation par rôle (agent / administrateur), et un design responsive. Les pages principales : connexion, tableau de bord (KPI et graphiques), analyse de crédit (formulaire et résultat avec jauge de risque et SHAP), détail d'analyse, clients, historique, assistant IA, notifications, utilisateurs, monitoring et profil.

---

## Installation

### Prérequis

- Python 3.11, Node.js, PostgreSQL
- Une clé API Groq (gratuite, sur console.groq.com)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows
source venv/bin/activate         # Linux/Mac

pip install -r requirements.txt

# Créer les bases
psql -U postgres -c "CREATE DATABASE credit_bsic;"
psql -U postgres -c "CREATE DATABASE mlflow_bsic;"

# Configurer le fichier .env (voir ci-dessous)
python -m app.init_db

# (Optionnel) Générer des données de démonstration
python -m app.generer_donnees_test

# Terminal 1 — MLflow
mlflow server --backend-store-uri postgresql://postgres:MOT_DE_PASSE@localhost:5432/mlflow_bsic --default-artifact-root ./mlflow/artifacts --host 127.0.0.1 --port 5000

# Terminal 2 — API
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Variables d'environnement (`backend/.env`)

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
| Interface (frontend)        | http://localhost:5173        |
| API FastAPI                 | http://localhost:8000        |
| Documentation API (Swagger) | http://localhost:8000/docs   |
| MLflow                      | http://localhost:5000        |

---

## Auteur

**Mémoire de master** — Modélisation prédictive du risque de défaut de paiement de crédit dans le secteur bancaire tchadien : apport du Machine Learning au scoring crédit, cas de la BSIC Tchad.

---

## Licence

Projet académique — usage pédagogique et démonstratif.
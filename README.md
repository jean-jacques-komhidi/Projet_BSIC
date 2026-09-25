# CREDISCORE-BSIC — Projet MLOps Complet

**Système de scoring crédit avec cycle de vie ML de bout en bout**

Plateforme MLOps complète de scoring crédit (prédiction du risque de défaut de paiement) développée dans le cadre d'un mémoire de master. Le projet couvre l'intégralité du cycle de vie d'un modèle de Machine Learning : de la préparation des données à l'entraînement, jusqu'au déploiement en production, à l'explicabilité (SHAP), à l'assistant conversationnel (LLM), au réentraînement asynchrone multi-modèles et au monitoring de la dérive des données. Cas d'application : la Banque Sahélo-Saharienne pour l'Investissement et le Commerce (BSIC Tchad).

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-Vite-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![MLflow](https://img.shields.io/badge/MLflow-Tracking-0194E2?style=flat-square&logo=mlflow&logoColor=white)](https://mlflow.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-Academic-lightgrey?style=flat-square)]()

---

## Table des matières

- [Contexte](#contexte)
- [Jeu de données](#jeu-de-données)
- [Stack technique](#stack-technique)
- [Étapes MLOps](#étapes-mlops)
- [Architecture technique](#architecture-technique)
- [Architecture du projet](#architecture-du-projet)
- [Résultats des modèles](#résultats-des-modèles)
- [Score métier](#score-métier)
- [Pipeline de réentraînement](#pipeline-de-réentraînement)
- [Analyse Data Drift](#analyse-data-drift)
- [Assistant conversationnel](#assistant-conversationnel)
- [Fonctionnalités de l'interface](#fonctionnalités-de-linterface)
- [Installation](#installation)
- [Pipeline CI/CD](#pipeline-cicd)
- [Auteur](#auteur)

---

## Contexte

| Élément | Détail |
|---------|--------|
| Nature | Mémoire de master — projet MLOps de scoring crédit |
| Objectif | Prédire le risque de défaut de paiement d'un demandeur de crédit |
| Institution | IUC — CEFOD Business School |
| Terrain | BSIC Tchad (secteur bancaire tchadien) |
| Périmètre | Préparation données → modélisation → API → interface → monitoring |
| Modèle retenu | Gradient Boosting (AUC-ROC 0,753) |

Le secteur bancaire tchadien se caractérise par une faible bancarisation et un taux élevé de créances en souffrance. Le projet démontre la mise en œuvre d'une chaîne MLOps industrialisée : suivi d'expériences (MLflow), API de prédiction (FastAPI), interface d'analyse (React), explicabilité des décisions (SHAP), assistant conversationnel (LLM), détection de dérive des données (z-score et PSI), réentraînement asynchrone multi-modèles et intégration continue (GitHub Actions), tout en respectant les exigences d'explicabilité du régulateur (COBAC).

---

## Jeu de données

**Home Credit Default Risk** (Kaggle), utilisé comme base de substitution en l'absence d'accès aux données réelles de la BSIC (secret bancaire).

| Caractéristique | Valeur |
|-----------------|--------|
| Dossiers | 307 511 |
| Variables retenues | 18 (correspondant à la fiche de prêt de la BSIC) |
| Cible | `TARGET` binaire (1 = défaut, 0 = sain) |
| Déséquilibre de classes | 91,9 % sains / 8,1 % en défaut |

Les variables ont été sélectionnées pour correspondre aux informations réellement collectées par la BSIC. Le déséquilibre est traité par pondération des classes.

---

## Stack technique

| Couche | Technologies |
|--------|--------------|
| Backend & API | FastAPI, Uvicorn, Python 3.11 |
| Machine Learning | LightGBM (Gradient Boosting), RandomForest, LogisticRegression, scikit-learn |
| Explicabilité | SHAP |
| Suivi d'expériences | MLflow (Tracking, Runs, Métriques) |
| Base de données | PostgreSQL (`credit_bsic`, `mlflow_bsic`) |
| Assistant (LLM) | Groq (API gratuite), LangChain |
| Monitoring | z-score statistique, PSI (Population Stability Index) |
| Génération PDF | ReportLab |
| Frontend | React, Vite, Tailwind CSS, Lucide React, Chart.js, React Markdown |
| Communication | Axios (HTTP), JWT (authentification) |
| CI/CD | GitHub Actions |

---

## Étapes MLOps

| Étape | Description | Statut |
|-------|-------------|--------|
| 1 | MLflow + PostgreSQL | OK |
| 2 | Préparation des données (feature engineering, pondération des classes) | OK |
| 3 | Score métier FP / FN | OK |
| 4 | Entraînement multi-modèles + explicabilité SHAP | OK |
| 5 | API FastAPI (authentification, scoring, CRUD) | OK |
| 6 | Interface React complète et responsive | OK |
| 7 | Data Drift (z-score + PSI) | OK |
| 8 | Réentraînement asynchrone multi-modèles + versioning MLflow | OK |
| 9 | Gestion clients CRUD + traçabilité des analyses | OK |
| 10 | Assistant conversationnel (mémoire + RAG) | OK |
| 11 | Boucle MLOps (résultat réel réinjecté au réentraînement) | OK |
| Bonus | CI/CD GitHub Actions + tests automatiques | OK |

---

## Architecture technique

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)           │
│   Connexion | Tableau de bord | Analyse | Détail    │
│   Clients | Historique | Assistant IA               │
│   Notifications | Utilisateurs | Monitoring | Profil│
│   Responsive mobile/desktop | Thème clair/sombre    │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP (Axios) + JWT
                      ▼
┌─────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI, port 8000)      │
│   /auth | /clients | /analyses | /conversations     │
│   /notifications | /dashboard | /monitoring | /drift│
│   Authentification JWT + rôles | Journalisation     │
└──────────┬─────────────────┬────────────────────────┘
           │                 │
    ┌──────┴──────┐   ┌──────┴──────────────────┐
    ▼             ▼   ▼                          ▼
┌──────────┐ ┌──────────┐ ┌────────────────────────┐
│ Service  │ │  MLflow  │ │      PostgreSQL         │
│ ML+SHAP  │ │ Port 5000│ │   credit_bsic           │
│ CrediBot │ │ Tracking │ │   - users, clients      │
│ (Groq)   │ │ Runs     │ │   - analyses            │
└──────────┘ │ Métriques│ │   - model_versions      │
             └──────────┘ │   - notifications       │
                          │   - conversations       │
                          │   - messages            │
                          └────────────────────────┘
```

---

## Architecture du projet

```
Projet_BSIC/
├── .github/workflows/ci.yml         # CI/CD GitHub Actions
├── backend/                         # API FastAPI + ML + MLflow
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py                # 7 tables (users, clients, analyses,
│   │   │                            # model_versions, notifications,
│   │   │                            # conversations, messages)
│   │   ├── security.py, database.py, logging_config.py, erreurs.py
│   │   ├── model_service.py         # Prédiction + SHAP
│   │   ├── explication.py           # Explication en langage naturel
│   │   ├── pdf_service.py           # Fiche PDF
│   │   ├── chatbot_service.py       # CrediBot (Groq)
│   │   ├── reentrainement.py, retrain_manager.py  # Réentraînement asynchrone
│   │   ├── monitoring_service.py    # Lecture MLflow
│   │   ├── drift_service.py         # Data drift (z-score, PSI)
│   │   ├── notification_service.py
│   │   ├── generer_donnees_test.py  # Données de démonstration
│   │   └── *_routes.py              # Routes par domaine
│   ├── tests/                       # Tests automatiques (CI)
│   ├── models/modele_credistore.pkl
│   ├── notebook/                    # Notebook, script MLflow, dataset
│   ├── requirements.txt, requirements-ci.txt
│   └── README.md
│
├── frontend/                        # Interface React + Tailwind
│   ├── src/
│   │   ├── components/ (layout, ui, ScoreForm, ScoreResult, ShapChart)
│   │   ├── context/ (Auth, Theme, Notifications)
│   │   ├── pages/ (Login, Dashboard, Analyse, Détail, Clients,
│   │   │           Historique, Assistant, Notifications,
│   │   │           Utilisateurs, Monitoring, Profil)
│   │   └── services/
│   ├── package.json
│   └── README.md
│
├── .gitignore
└── README.md
```

---

## Résultats des modèles

Trois modèles sont entraînés et comparés à chaque cycle. Le pipeline sélectionne et déploie automatiquement le meilleur.

| Modèle | AUC-ROC (test) | Coût métier |
|--------|----------------|-------------|
| Régression logistique | 0,740 | 21 446 |
| Random Forest | 0,737 | 21 997 |
| **Gradient Boosting** | **0,753** | **20 868** |

Le Gradient Boosting obtient la meilleure performance, à la fois en AUC et en coût métier. Il est sélectionné et déployé en production.

---

## Score métier

Dans le contexte du scoring crédit, les deux types d'erreurs n'ont pas le même coût :

| Erreur | Signification | Coût |
|--------|---------------|------|
| Faux négatif (FN) | Accorder un crédit à un futur défaut | 5 |
| Faux positif (FP) | Refuser un bon client | 1 |

**Formule** : `Coût = (5 × FN) + (1 × FP)` — à minimiser.

**Seuil de décision** : 0,70, calculé pour minimiser le coût métier, reflétant le fait qu'un défaut de remboursement coûte cinq fois plus cher qu'une opportunité manquée.

---

## Pipeline de réentraînement

Le réentraînement s'exécute de manière asynchrone (en tâche de fond), avec un suivi de progression en temps réel affiché dans l'interface de monitoring.

```
Données socle (application_train)
         +
Analyses réelles résolues (résultat renseigné : remboursé / défaut)
                    |
         Préparation + pondération des classes
                    |
    Régression logistique | Random Forest | Gradient Boosting
                    |
       Comparaison AUC-ROC + coût métier
                    |
      Meilleur modèle → modele_credistore.pkl
                    |
     Nouvelle version en base + marquée en production
                    |
             Enregistrement dans MLflow
```

La boucle MLOps est complète : l'agent renseigne l'issue réelle du crédit depuis l'interface, ces données enrichissent le réentraînement, et le modèle s'améliore au fil du temps.

---

## Analyse Data Drift

La détection du drift utilise le z-score statistique, complété par le PSI :

`Z = |moyenne_production - moyenne_référence| / écart_type_référence`

| Seuil | Statut | Action |
|-------|--------|--------|
| Z ≤ 1 | NORMAL | Distribution stable |
| 1 < Z ≤ 2 | ALERTE | Dérive modérée à surveiller |
| Z > 2 | CRITIQUE | Réentraînement recommandé |

Pour chaque variable surveillée (revenu, montant du crédit, mensualité, âge, ancienneté), l'application affiche l'écart en pourcentage, le z-score, les moyennes de référence et de production, et le statut. Une dérive importante déclenche une notification.

---

## Assistant conversationnel

**CrediBot**, l'assistant intelligent de l'application, répond aux questions de l'agent en langage naturel avec deux mécanismes : les questions sur les données (statistiques et liste des clients) et les questions sur un dossier précis (RAG). Il dispose d'une mémoire conversationnelle et d'un historique des conversations sauvegardé, groupé par date. Les réponses sont mises en forme (Markdown). Le modèle de langage est appelé via l'API gratuite de Groq.

---

## Fonctionnalités de l'interface

| Page | Fonctionnalités |
|------|----------------|
| Tableau de bord | KPI, graphiques Chart.js animés, activité récente, statut du modèle |
| Analyse | Recherche client, formulaire par sections, jauge de risque, explication SHAP |
| Détail d'analyse | Résultat complet, résultat réel (boucle MLOps), lien vers CrediBot |
| Clients | Liste, recherche, CRUD complet |
| Historique | Filtres, recherche, accès au détail |
| Assistant IA | CrediBot : mémoire, historique, réponses en Markdown |
| Notifications | Journal des événements, badge de non-lues |
| Utilisateurs | CRUD des comptes et rôles (admin) |
| Monitoring | MLflow, réentraînement temps réel, data drift détaillé (admin) |
| Profil | Informations, statistiques d'activité, changement de mot de passe |

---

## Installation

### Prérequis

- Python 3.11, Node.js 18+, PostgreSQL

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate         # Windows
source venv/bin/activate      # Linux/Mac
pip install -r requirements.txt

psql -U postgres -c "CREATE DATABASE credit_bsic;"
psql -U postgres -c "CREATE DATABASE mlflow_bsic;"
python -m app.init_db
python -m app.generer_donnees_test   # (optionnel) données de démonstration

# Terminal 1 — MLflow
mlflow server --backend-store-uri postgresql://postgres:MOT_DE_PASSE@localhost:5432/mlflow_bsic --default-artifact-root ./mlflow/artifacts --host 127.0.0.1 --port 5000

# Terminal 2 — API FastAPI
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Accès aux services

| Service | URL |
|---------|-----|
| Frontend React | http://localhost:5173 |
| API FastAPI | http://localhost:8000 |
| Documentation API (Swagger) | http://localhost:8000/docs |
| MLflow UI | http://localhost:5000 |

---

## Pipeline CI/CD

```
Push sur main
     │
     ▼
┌────────────────┐
│  Test Backend  │
│  - imports OK  │
│  - modèle OK   │
│  - explication OK │
│  - sécurité OK │
└───────┬────────┘
        ▼
  Résultat (vert / rouge) sur GitHub Actions
```

À chaque push, GitHub Actions installe les dépendances, vérifie les imports des modules clés et exécute les tests automatiques (modèle, explication, sécurité).

---

## Auteur

**KOMHIDI Jean-Jacques**
Master — IUC / CEFOD Business School

Mémoire : Modélisation prédictive du risque de défaut de paiement de crédit
dans le secteur bancaire tchadien : apport du Machine Learning au scoring crédit,
cas de la BSIC Tchad.

Année : 2025 / 2026

---

## Licence

Projet académique — usage pédagogique et démonstratif.
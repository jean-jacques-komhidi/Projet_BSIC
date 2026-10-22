# CREDISCORE — Scoring crédit et MLOps pour la BSIC Tchad

**Application de scoring crédit avec le cycle de vie complet d'un modèle de Machine Learning : de l'entraînement à la surveillance en production.**

CREDISCORE aide les agents de crédit à évaluer le risque de défaut d'un demandeur, explique chaque décision, et permet à l'administrateur de surveiller le modèle, de le réentraîner sur les issues réelles et de le remplacer seulement s'il fait mieux. Projet réalisé dans le cadre d'un mémoire de master, appliqué à la Banque Sahélo-Saharienne pour l'Investissement et le Commerce (BSIC Tchad).

[![CI](https://github.com/jean-jacques-komhidi/Projet_BSIC/actions/workflows/ci.yml/badge.svg)](https://github.com/jean-jacques-komhidi/Projet_BSIC/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-Vite-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![MLflow](https://img.shields.io/badge/MLflow-Tracking-0194E2?style=flat-square&logo=mlflow&logoColor=white)](https://mlflow.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-base-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Render](https://img.shields.io/badge/Déployé_sur-Render-46E3B7?style=flat-square&logo=render&logoColor=white)](https://crediscore-frontend.onrender.com)

**Démo en ligne :** [crediscore-frontend.onrender.com](https://crediscore-frontend.onrender.com) — hébergement gratuit : le premier chargement peut prendre une minute, le temps que le serveur se réveille.

<p align="center"><img src="docs/demo.gif" alt="Démonstration : analyse d'un dossier, recherche, détail du client et CrediBot" width="900"></p>
<p align="center"><sub>Une agente analyse un dossier, retrouve un client avec Ctrl K, consulte son parcours puis CrediBot.</sub></p>

---

## Sommaire

- [Contexte](#contexte)
- [La boucle MLOps en un coup d'œil](#la-boucle-mlops-en-un-coup-dœil)
- [Fonctionnalités](#fonctionnalités)
- [Jeu de données et modèle](#jeu-de-données-et-modèle)
- [Surveillance du modèle](#surveillance-du-modèle)
- [Réentraînement : champion et challenger](#réentraînement--champion-et-challenger)
- [CrediBot, l'assistant](#credibot-lassistant)
- [Sécurité et protection des données](#sécurité-et-protection-des-données)
- [Architecture](#architecture)
- [Aperçu de l'interface](#aperçu-de-linterface)
- [Installation en local](#installation-en-local)
- [Déploiement](#déploiement)
- [Tests et intégration continue](#tests-et-intégration-continue)
- [Limites et perspectives](#limites-et-perspectives)
- [Auteur](#auteur)

---

## Contexte

| Élément | Détail |
|---------|--------|
| Nature | Mémoire de master — projet MLOps de scoring crédit |
| Objectif | Prédire le risque de défaut de paiement d'un demandeur de crédit |
| Terrain | BSIC Tchad (secteur bancaire tchadien) |
| Utilisateurs | Agents de crédit et administrateur |
| Modèle en service | Gradient Boosting (LightGBM), AUC 0,753 à l'entraînement |

Le secteur bancaire tchadien se caractérise par une faible bancarisation et un taux élevé de créances en souffrance. CREDISCORE propose un scoring fondé sur l'apprentissage automatique, explicable comme l'exige le régulateur (COBAC), et suivi dans le temps : un modèle de crédit vieillit à mesure que la clientèle et l'économie changent.

---

## La boucle MLOps en un coup d'œil

```mermaid
flowchart LR
    A[1. L'agent saisit<br>le dossier] --> B[2. Score, décision<br>et explication SHAP]
    B --> C[3. Fiche PDF<br>signée en agence]
    C --> D[4. L'issue réelle<br>est renseignée]
    D --> E[5. Surveillance :<br>dérive et performance]
    E -->|règle atteinte| F[6. Réentraînement<br>champion / challenger]
    F -->|meilleur modèle| B
```

Chaque crédit accordé finit par être remboursé ou par faire défaut. Cette issue réelle, renseignée dans l'application, sert à mesurer la performance du modèle en production puis à l'améliorer : c'est ce qui distingue un projet MLOps d'un modèle entraîné une seule fois.

---

## Fonctionnalités

| Fonctionnalité | Ce qu'elle fait | Accès |
|----------------|-----------------|-------|
| Analyse de crédit | Probabilité de défaut, décision, jauge de risque, facteurs SHAP et explication en langage clair | Agent, admin |
| Détail d'un dossier | Parcours du client, ce qui a changé depuis la dernière analyse, simulation d'un autre montant ou d'une autre durée | Agent, admin |
| Fiche de décision PDF | Fiche imprimable avec QR code d'authenticité, pour le dossier physique | Agent, admin |
| Clients et historique | Gestion des clients, historique filtrable de toutes les analyses | Agent, admin |
| Recherche globale | Barre du haut (Ctrl K) : clients, références CRED-AAAA-NNNN, pages et actions | Agent, admin |
| CrediBot | Assistant en langage naturel, réponses en continu, dossier joint à la conversation | Agent, admin |
| Notifications | Alertes du modèle, clients dont le risque monte, issues à renseigner | Agent, admin |
| Profil | Bilan de sécurité, statistiques sur 12 mois, thème clair, sombre ou système | Agent, admin |
| Issue réelle | Indiquer si un crédit a été remboursé ou a fait défaut (boucle MLOps) | Admin |
| Monitoring | Dérive des données (PSI), performance réelle, règle de réentraînement, versions du modèle | Admin |
| Réentraînement | Nouveau modèle entraîné en tâche de fond, mis en service seulement s'il fait mieux | Admin |
| Export des données | CSV (Power BI, Excel) ou Excel, noms anonymisables, dictionnaire des données, journal des exports | Admin |
| Utilisateurs | Comptes des agents et rôles | Admin |

---

## Jeu de données et modèle

**Home Credit Default Risk** (Kaggle), utilisé comme base de substitution faute d'accès aux données réelles de la BSIC (secret bancaire).

| Caractéristique | Valeur |
|-----------------|--------|
| Dossiers | 307 511 |
| Variables retenues | 18, alignées sur la fiche de prêt de la BSIC |
| Cible | `TARGET` (1 = défaut, 0 = remboursé) |
| Déséquilibre | 91,9 % remboursés, 8,1 % en défaut (traité par pondération des classes) |

Trois modèles ont été comparés ; le Gradient Boosting est retenu.

| Modèle | AUC (test) | Coût métier |
|--------|-----------|-------------|
| Régression logistique | 0,740 | 21 446 |
| Random Forest | 0,737 | 21 997 |
| **Gradient Boosting** | **0,753** | **20 868** |

**Coût métier.** Accorder un crédit à un futur défaut (faux négatif) coûte 5 ; refuser un bon client (faux positif) coûte 1 : `Coût = 5 × FN + 1 × FP`. Le seuil de décision, **70 %** de probabilité de défaut, minimise ce coût. L'interface classe le risque en faible (moins de 40 %), moyen (40 à 70 %) et élevé (70 % et plus).

---

## Surveillance du modèle

La page Monitoring répond à trois questions, toutes calculées sur les analyses enregistrées dans l'application.

| Niveau | Question | Mesure |
|--------|----------|--------|
| Données | Les dossiers récents ressemblent-ils à ceux de référence ? | PSI par variable (30 derniers jours contre la période de référence) |
| Prédictions | Le modèle refuse-t-il plus ou moins qu'avant ? | PSI des probabilités de défaut, évolution du taux de refus |
| Performance | Le modèle se trompe-t-il sur les crédits dont on connaît l'issue ? | AUC réelle, défaut prédit contre défaut constaté, par mois d'octroi |

**PSI** (indice de stabilité de la population) : moins de 0,10 stable, 0,10 à 0,25 dérive modérée, plus de 0,25 dérive forte. Avec peu de dossiers, le PSI varie par simple hasard : une dérive n'est retenue que si elle est **statistiquement significative** (test du khi-deux, p < 0,05).

**Règle de réentraînement**, fixée à l'avance. Le réentraînement est recommandé dès qu'une condition est atteinte :

1. Dérive forte (PSI > 0,25) sur une variable importante ;
2. Baisse de l'AUC réelle de plus de 0,05 par rapport à l'entraînement, ou AUC sous 0,70 ;
3. Écart de plus de 8 points entre le défaut prédit et le défaut constaté.

Les conditions 2 et 3 demandent au moins 50 issues réelles. La décision reste humaine : l'administrateur est notifié, puis lance lui-même le réentraînement.

---

## Réentraînement : champion et challenger

```mermaid
flowchart TD
    A[Socle Home Credit<br>307 511 dossiers] --> C
    B[Issues réelles de la banque<br>remboursé ou défaut] --> C
    C[Apprentissage<br>les issues réelles pèsent 30 %] --> D[Régression logistique · Random Forest · Gradient Boosting]
    D --> E[Meilleur candidat]
    E --> F([Comparaison avec le modèle en service<br>sur des issues réelles mises de côté])
    F -->|Meilleure AUC| G[Mis en service<br>nouvelle version, enregistrée dans MLflow]
    F -->|Sinon| H[Candidat écarté<br>le modèle actuel reste en service]
```

- Les issues réelles sont peu nombreuses face au socle : on leur donne **30 % du poids** de l'apprentissage, comme une banque privilégie ses données locales et récentes.
- Le candidat et le modèle en service sont jugés **sur les mêmes issues réelles, jamais vues à l'entraînement**. Le candidat ne remplace le champion que s'il fait mieux.
- Après une mise en service, la référence de la surveillance devient les quatre derniers mois, et la performance est mesurée sur les décisions du nouveau modèle uniquement.
- Le réentraînement tourne en tâche de fond, avec une barre de progression ; chaque version est conservée avec son AUC d'entraînement, son AUC réelle et sa date de mise en service ou de retrait.

---

## CrediBot, l'assistant

CrediBot répond en langage naturel aux questions des agents : « Quel est le client le plus risqué ? », « Pourquoi ce dossier a-t-il été refusé ? », « Avec un montant plus faible, passerait-il ? ».

- **Contexte réel** : statistiques du portefeuille, fiches des clients cités, et le dossier joint à la conversation (bouton « Joindre un dossier »).
- **Réponses en continu**, mises en forme (listes, tableaux), avec un bouton pour télécharger la fiche PDF quand elle est proposée.
- **Historique** des conversations, rangé par période, avec un aperçu de la dernière réponse.
- **Confidentialité** : les noms des clients sont remplacés par des codes (`Client#12`) avant l'envoi au modèle de langage, puis rétablis à l'affichage.
- Modèle de langage : `openai/gpt-oss-120b` via l'API Groq.

---

## Sécurité et protection des données

| Mesure | Détail |
|--------|--------|
| Authentification | Jetons JWT signés (HS256) ; mots de passe hachés avec bcrypt |
| Mots de passe | 8 caractères minimum, majuscule, minuscule et chiffre, sans le nom ni l'e-mail ; date du dernier changement suivie |
| Rôles | Agent ou administrateur, vérifiés côté API (pas seulement dans l'interface) |
| Secrets | Aucun dans le dépôt : fichier `.env` local (modèle : `backend/.env.exemple`) ou variables d'environnement de Render |
| Assistant | Noms des clients pseudonymisés avant l'envoi à Groq |
| Export | Réservé à l'administrateur ; destinataire et motif obligatoires ; noms anonymisables ; genre exclu par défaut ; chaque export est journalisé ; mots de passe et conversations jamais exportés |
| Traçabilité | Suppressions d'analyses journalisées et notifiées à l'administrateur |

---

## Architecture

```mermaid
flowchart LR
    U[Navigateur<br>React + Vite] -->|HTTPS, JWT| API[API FastAPI]
    API --> DB[(PostgreSQL)]
    API --> ML[Modèle LightGBM<br>+ SHAP]
    API --> G[Groq<br>CrediBot]
    API --> MF[MLflow<br>suivi des entraînements]
```

| Couche | Technologies |
|--------|--------------|
| Interface | React 19, Vite, Tailwind CSS 4, React Router, Chart.js, Lucide, React Markdown |
| API | FastAPI, Uvicorn, SQLAlchemy, Pydantic, python-jose (JWT), passlib (bcrypt) |
| Machine Learning | scikit-learn, LightGBM, SHAP, SciPy |
| Suivi des modèles | MLflow |
| Documents | ReportLab (fiche PDF avec QR code), openpyxl (export Excel) |
| Assistant | API Groq |
| Base de données | PostgreSQL (SQLite pour les tests) |
| Intégration continue | GitHub Actions |
| Hébergement | Render (API, site statique, PostgreSQL) |

<details>
<summary><b>Routes de l'API</b></summary>

| Préfixe | Rôle |
|---------|------|
| `/auth` | Connexion, profil, mot de passe, utilisateurs |
| `/clients` | Clients |
| `/analyses` | Analyses, simulation, fiche PDF, issue réelle |
| `/dashboard` | Indicateurs du tableau de bord |
| `/recherche` | Recherche globale |
| `/conversations`, `/chatbot` | CrediBot |
| `/notifications` | Notifications |
| `/monitoring`, `/reentrainer` | Surveillance et réentraînement |
| `/export` | Export des données et journal |

La documentation interactive est sur `/docs` (Swagger).
</details>

<details>
<summary><b>Base de données</b></summary>

```mermaid
erDiagram
    users ||--o{ analyses : realise
    clients ||--o{ analyses : concerne
    model_versions ||--o{ analyses : produit
    users ||--o{ conversations : ouvre
    conversations ||--o{ messages : contient
    analyses ||--o{ conversations : "dossier joint"
    users ||--o{ notifications : recoit
    users ||--o{ exports_donnees : effectue
    analyses {
        int id
        float probabilite_defaut
        string decision
        string resultat_reel
        datetime date_analyse
    }
    model_versions {
        int id
        string algorithme
        float auc
        float auc_reelle
        bool en_production
        string statut
    }
```

Neuf tables : `users`, `clients`, `analyses`, `model_versions`, `notifications`, `conversations`, `messages`, `exports_donnees`, `etat_surveillance`.
</details>

<details>
<summary><b>Structure du dépôt</b></summary>

```
Projet_BSIC/
├── .github/workflows/ci.yml      # Tests automatiques à chaque push
├── render.yaml                   # Déploiement sur Render
├── backend/
│   ├── app/
│   │   ├── main.py               # Point d'entrée de l'API
│   │   ├── models.py             # Tables
│   │   ├── *_routes.py           # Routes par domaine
│   │   ├── model_service.py      # Prédiction et SHAP
│   │   ├── surveillance_service.py  # PSI, performance réelle, règle
│   │   ├── reentrainement.py     # Champion / challenger
│   │   ├── chatbot_service.py    # CrediBot
│   │   ├── export_service.py     # Export CSV / Excel
│   │   ├── pdf_service.py        # Fiche de décision
│   │   ├── init_db.py            # Création et mise à jour des tables
│   │   ├── creer_admin.py        # Premier administrateur
│   │   └── generer_donnees_test.py  # Données de démonstration
│   ├── models/modele_credistore.pkl
│   ├── notebook/                 # Notebook et script d'entraînement MLflow
│   └── tests/                    # 90 tests (pytest)
├── frontend/
│   └── src/
│       ├── pages/                # Une page par écran
│       ├── components/           # Barre du haut, menu, recherche, graphiques
│       ├── context/              # Session, thème, notifications
│       └── services/             # Appels à l'API
└── docs/screenshots/
```
</details>

---

## Aperçu de l'interface

<table>
<tr>
<td width="50%" valign="top"><b>Analyse de crédit</b><br><img src="docs/screenshots/03_analyse.png" alt="Analyse de crédit"></td>
<td width="50%" valign="top"><b>Détail d'un dossier</b><br><img src="docs/screenshots/04_detail_analyse.png" alt="Détail d'un dossier"></td>
</tr>
<tr>
<td width="50%" valign="top"><b>Monitoring</b><br><img src="docs/screenshots/10_monitoring.png" alt="Monitoring"></td>
<td width="50%" valign="top"><b>CrediBot</b><br><img src="docs/screenshots/07_credibot.png" alt="CrediBot"></td>
</tr>
<tr>
<td width="50%" valign="top"><b>Fiche de décision (PDF)</b><br><img src="docs/screenshots/04b_fiche_pdf.png" alt="Fiche de décision (PDF)"></td>
<td width="50%" valign="top"><b>Export des données</b><br><img src="docs/screenshots/11_export.png" alt="Export des données"></td>
</tr>
</table>

<details>
<summary><b>Autres écrans</b> : connexion, tableau de bord, clients, historique, recherche, notifications, profil, utilisateurs, MLflow</summary>

<table>
<tr>
<td width="50%" valign="top"><b>Connexion</b><br><img src="docs/screenshots/01_connexion.png" alt="Connexion"></td>
<td width="50%" valign="top"><b>Tableau de bord</b><br><img src="docs/screenshots/02_tableau_de_bord.png" alt="Tableau de bord"></td>
</tr>
<tr>
<td width="50%" valign="top"><b>Clients</b><br><img src="docs/screenshots/05_clients.png" alt="Clients"></td>
<td width="50%" valign="top"><b>Historique des analyses</b><br><img src="docs/screenshots/06_historique.png" alt="Historique des analyses"></td>
</tr>
<tr>
<td width="50%" valign="top"><b>Recherche globale (Ctrl K)</b><br><img src="docs/screenshots/13_recherche.png" alt="Recherche globale (Ctrl K)"></td>
<td width="50%" valign="top"><b>Notifications</b><br><img src="docs/screenshots/08_notifications.png" alt="Notifications"></td>
</tr>
<tr>
<td width="50%" valign="top"><b>Profil</b><br><img src="docs/screenshots/12_profil.png" alt="Profil"></td>
<td width="50%" valign="top"><b>Utilisateurs</b><br><img src="docs/screenshots/09_utilisateurs.png" alt="Utilisateurs"></td>
</tr>
<tr>
<td width="50%" valign="top"><b>Suivi des entraînements (MLflow)</b><br><img src="docs/screenshots/18_mlflow_ui.png" alt="Suivi des entraînements (MLflow)"></td>
<td></td>
</tr>
</table>
</details>

Les noms et montants des captures sont des données de démonstration.

---

## Installation en local

**Prérequis :** Python 3.11, Node.js 18 ou plus, PostgreSQL, une clé API Groq (gratuite sur [console.groq.com](https://console.groq.com)).

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows  (Linux/Mac : source venv/bin/activate)
pip install -r requirements.txt
```

Copiez `backend/.env.exemple` en `backend/.env` et remplissez-le (mot de passe PostgreSQL, `SECRET_KEY`, `GROQ_API_KEY`, premier administrateur).

```bash
psql -U postgres -c "CREATE DATABASE credit_bsic;"
psql -U postgres -c "CREATE DATABASE mlflow_bsic;"
python -m app.init_db                 # crée les tables
python -m app.creer_admin             # crée l'administrateur défini dans .env
python -m app.generer_donnees_test    # (facultatif) 18 mois de données de démonstration
```

Pour le réentraînement, placez `application_train.csv` ([Kaggle](https://www.kaggle.com/competitions/home-credit-default-risk/data)) dans `backend/notebook/`. Il n'est pas publié dans le dépôt en raison de sa taille.

### 2. Lancer les trois serveurs

```bash
# Terminal 1 — MLflow (dans backend, venv activé)
mlflow server --backend-store-uri postgresql://postgres:MOT_DE_PASSE@localhost:5432/mlflow_bsic --default-artifact-root ./mlflow/artifacts --host 127.0.0.1 --port 5000

# Terminal 2 — API (dans backend, venv activé)
uvicorn app.main:app --reload --port 8000

# Terminal 3 — Interface
cd frontend
npm install
npm run dev
```

| Service | Adresse |
|---------|---------|
| Interface | http://localhost:5173 |
| API | http://localhost:8000 |
| Documentation de l'API | http://localhost:8000/docs |
| MLflow | http://127.0.0.1:5000 |

---

## Déploiement

Le fichier [`render.yaml`](render.yaml) décrit les trois services Render : la base PostgreSQL, l'API FastAPI et l'interface (site statique). La branche `deploiement-render` est déployée automatiquement à chaque mise à jour.

Les secrets (`GROQ_API_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`) sont saisis dans Render, jamais dans le dépôt ; `SECRET_KEY` est générée par Render. Au démarrage, l'API crée ou met à jour les tables puis le premier administrateur.

---

## Tests et intégration continue

90 tests automatiques (pytest) couvrent le modèle, l'explication, la sécurité, les droits de l'administrateur, les clients, l'historique, le tableau de bord, la surveillance, la fiche PDF, l'export, le profil, la recherche et CrediBot. Ils tournent sur une base SQLite temporaire, sans toucher aux données.

```bash
cd backend
pytest tests/ -q
```

À chaque push sur `main`, GitHub Actions installe les dépendances, vérifie les imports des modules clés et lance les tests.

---

## Limites et perspectives

| Limite actuelle | Piste d'amélioration |
|-----------------|----------------------|
| Le modèle est entraîné sur un jeu de données public (Home Credit), faute d'accès aux données de la BSIC | Réentraîner sur l'historique réel de la banque ; la boucle MLOps est prête à l'accueillir |
| Les issues réelles de la démonstration sont simulées | Les renseigner au fil des remboursements réels |
| CrediBot s'appuie sur un service externe (Groq), même avec des noms pseudonymisés | Héberger un modèle de langage dans l'infrastructure de la banque |
| Hébergement gratuit : mise en veille et ressources limitées | Serveur de la banque ou offre payante, avec sauvegardes de la base |
| Pas de limite de tentatives de connexion | Blocage temporaire après plusieurs échecs, double authentification pour l'administrateur |

---

## Auteur

**KOMHIDI Jean-Jacques** — Master, UCAO

- Encadrant : **Chamsedine Aidara**
- Mémoire : *Modélisation prédictive du risque de défaut de paiement de crédit dans le secteur bancaire tchadien : apport du Machine Learning au scoring crédit, cas de la BSIC Tchad.*
- Année universitaire 2025-2026

## Licence

Projet académique, à usage pédagogique et démonstratif.

# Frontend — CREDISCORE-BSIC

## Description
Interface web React pour le système de scoring crédit de la BSIC Tchad. Elle permet aux agents de crédit et aux administrateurs d'analyser des dossiers, d'obtenir un score de risque avec explication, de dialoguer avec un assistant intelligent, et de superviser le modèle. L'interface est entièrement responsive (mobile et desktop) avec un thème clair/sombre, et une navigation adaptée au rôle de l'utilisateur.

## Stack technique
| Outil | Rôle |
|-------|------|
| React + Vite | Framework frontend |
| Tailwind CSS | Styling responsive |
| Lucide React | Icônes |
| Axios | Appels HTTP vers l'API FastAPI |
| React Router DOM | Navigation entre pages |
| Chart.js | Graphiques du tableau de bord et du monitoring |
| React Markdown | Rendu des réponses de l'assistant (tableaux, listes) |

## Structure du projet
```
frontend/src/
├── components/
│   ├── layout/
│   │   ├── Sidebar.jsx          # Navigation latérale (desktop + drawer mobile), par rôle
│   │   └── Layout.jsx           # Disposition générale (sidebar + contenu)
│   ├── ui/
│   │   ├── Header.jsx           # En-tête (titre, thème, profil)
│   │   ├── MetricCard.jsx       # Carte de KPI
│   │   └── JaugeScore.jsx       # Jauge de vitesse (score de risque)
│   ├── ScoreForm.jsx            # Formulaire de saisie du dossier
│   ├── ScoreResult.jsx          # Résultat + speedometer animé + explication
│   └── ShapChart.jsx            # Facteurs SHAP avec barres de contribution
├── context/
│   ├── ThemeContext.jsx         # Thème clair/sombre (persistant)
│   ├── AuthContext.jsx          # Utilisateur connecté et rôle
│   └── NotificationsContext.jsx # Compteur de notifications non lues
├── pages/
│   ├── LoginPage.jsx            # Connexion (fond animé, thème)
│   ├── DashboardPage.jsx        # Tableau de bord (KPI, graphiques, activité)
│   ├── AnalysePage.jsx          # Recherche client + analyse de crédit
│   ├── AnalyseDetailPage.jsx    # Détail d'une analyse + résultat réel + CrediBot
│   ├── ClientsPage.jsx          # Liste clients + CRUD + recherche
│   ├── HistoriquePage.jsx       # Historique des analyses (filtres, recherche)
│   ├── AssistantPage.jsx        # Assistant CrediBot (mémoire, historique)
│   ├── NotificationsPage.jsx    # Journal des notifications
│   ├── UtilisateursPage.jsx     # Gestion des utilisateurs (admin)
│   ├── UtilisateurFormPage.jsx  # Création / modification d'un utilisateur
│   ├── MonitoringPage.jsx       # MLflow + Data Drift + réentraînement
│   └── ProfilPage.jsx           # Profil, statistiques, sécurité
├── services/                    # Appels API centralisés (auth, clients,
│                                # analyses, chatbot, monitoring, etc.)
├── App.jsx                      # Routing principal (routes protégées par rôle)
└── index.css                    # Styles globaux + thèmes
```

## Pages de l'application

### Connexion
- Formulaire e-mail / mot de passe avec affichage/masquage du mot de passe
- Fond animé (formes floutées aux couleurs BSIC)
- Support du thème clair/sombre

### Tableau de bord
- Cartes de KPI (dossiers analysés, taux d'accord, refusés, risque moyen)
- Graphiques Chart.js animés (décisions, répartition des risques, évolution)
- Tableau des dernières analyses (client, revenu, risque, décision)
- Bandeau de statut de l'API et du modèle en production

### Analyse de crédit
- Recherche du client par nom (autocomplétion)
- Fiche client, puis formulaire en sections (profil, crédit, scores)
- Pré-remplissage et verrouillage des champs issus du client
- Résultat : jauge de vitesse animée, décision, explication en langage naturel
- Facteurs SHAP avec barres de contribution
- Export de la fiche de décision en PDF

### Détail d'une analyse
- Récapitulatif (client, numéro, date)
- Résultat complet (jauge, explication, facteurs SHAP)
- Renseignement du résultat réel (remboursé / défaut) — boucle MLOps
- Bouton « Interroger CrediBot » (conversation contextuelle sur le dossier)

### Clients
- Tableau avec recherche par nom
- Création, modification, suppression (modale)

### Historique
- Liste de toutes les analyses, filtres (toutes / accordées / refusées)
- Recherche par nom de client
- Accès au détail par clic

### Assistant IA (CrediBot)
- Interface de conversation épurée (style flux vertical)
- Mémoire conversationnelle et historique des conversations (groupé par date)
- Réponses mises en forme (Markdown : tableaux, listes)
- Questions sur les statistiques ou sur un dossier précis (RAG)

### Notifications
- Journal des événements (réentraînement, dérive)
- Distinction lues / non-lues, marquage comme lu

### Utilisateurs (admin)
- Liste des comptes avec rôle (agent / administrateur)
- Création et modification via des pages dédiées

### Monitoring (admin)
- 4 KPI : meilleur AUC-ROC, coût métier, expériences, statut de dérive
- Bouton de réentraînement avec barre de progression en temps réel (polling)
- Résultat du dernier réentraînement (AUC avant / après)
- Tableau des runs MLflow
- Data Drift détaillé par variable (écart, z-score, référence vs production)

### Profil
- Informations personnelles éditables
- Statistiques d'activité (analyses réalisées, accordés, refusés)
- Section sécurité : changement de mot de passe (avec vérification de l'ancien)

## Installation

### Prérequis
- Node.js >= 18
- npm >= 9

### Étapes
```bash
cd frontend
npm install
npm run dev
```

L'application sera disponible sur : http://localhost:5173

### Build pour la production
```bash
npm run build
```

## Configuration de l'adresse de l'API
L'adresse de l'API est définie dans `src/services/api.js` :
```javascript
const API_URL = "http://127.0.0.1:8000";
```

## Fonctionnalités
- Thème clair / sombre avec persistance
- Navigation adaptée au rôle (agent / administrateur)
- Authentification par jeton (JWT), routes protégées
- Jauge de vitesse animée pour le score de risque
- Facteurs SHAP visualisés avec barres de contribution
- Assistant conversationnel avec mémoire et historique
- Réentraînement multi-modèles avec suivi de progression
- Data Drift avec z-score et interprétation par variable
- Interface entièrement responsive (mobile et desktop)

## Design
- Couleur d'accent : bleu BSIC ; vert pour « accordé », rouge pour « refusé »
- Cartes arrondies, icônes sobres, badges à bordure colorée
- Transitions et animations légères
- Sidebar organisée par sections (Principal, Assistant, Administration, Compte)

## Auteur
**KOMHIDI Jean Jacques** — Master, IUC / CEFOD Business School
Mémoire : Modélisation prédictive du risque de défaut de paiement de crédit
dans le secteur bancaire tchadien, cas de la BSIC Tchad.
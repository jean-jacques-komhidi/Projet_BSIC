# Frontend — interface CREDISCORE

Interface React de CREDISCORE pour les agents de crédit et l'administrateur. La présentation générale du projet est dans le [README principal](../README.md).

## Démarrer

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

L'API doit tourner sur http://127.0.0.1:8000. Pour une autre adresse, définissez `VITE_API_URL` au moment du build :

```bash
VITE_API_URL=https://mon-api.exemple.com npm run build
```

## Pile

React 19, Vite, Tailwind CSS 4, React Router, Axios, Chart.js, Lucide, React Markdown.

## Organisation

| Dossier | Contenu |
|---------|---------|
| `pages/` | Un fichier par écran : tableau de bord, analyse, détail, clients, historique, assistant, notifications, profil ; pour l'administrateur : utilisateurs, monitoring, export |
| `components/layout/` | Menu latéral et disposition générale |
| `components/ui/` | Barre du haut, recherche globale (Ctrl K), cartes, confirmations |
| `components/` | Formulaire d'analyse, résultat, graphique SHAP |
| `context/` | Session et rôle, thème (clair, sombre, système), notifications non lues |
| `services/` | Un fichier d'appels à l'API par domaine |
| `utils/` | Petits utilitaires (éléments consultés récemment) |

## Repères

- Les pages réservées à l'administrateur sont protégées dans le routage et, surtout, par l'API.
- Le thème suit le choix de l'utilisateur, ou le réglage de l'appareil en mode « système ».
- Couleurs : bleu BSIC pour les actions, vert pour « accordé », orange pour « moyen », rouge pour « refusé ».

## Construire pour la production

```bash
npm run build        # fichiers statiques dans dist/
```

// Configuration centrale de la communication avec l'API backend

import axios from "axios";

// Adresse de base de ton API (le backend FastAPI)
// En production, VITE_API_URL est fournie au moment du build (ex. par Render).
// Render ne donne que le nom d'hote : on ajoute https:// si besoin.
// En local, on garde l'adresse habituelle.
const brut = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const API_URL = /^https?:\/\//.test(brut) ? brut : `https://${brut}`;

// Création d'une instance axios configurée
const api = axios.create({
  baseURL: API_URL,
});

// Intercepteur : ajoute automatiquement le jeton à chaque requête
// (le jeton est stocké dans le navigateur après la connexion)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Intercepteur : si le jeton est expiré (erreur 401), on déconnecte
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem("token");
      // On pourra rediriger vers la page de connexion ici
    }
    return Promise.reject(error);
  }
);

export default api;
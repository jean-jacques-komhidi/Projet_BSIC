// Service d'authentification : connexion, déconnexion, utilisateur courant

import api from "./api";

// Connexion : envoie email + mot de passe, récupère et stocke le jeton
export async function seConnecter(email, motDePasse) {
  // L'API attend un formulaire (username = email, password)
  const params = new URLSearchParams();
  params.append("username", email);
  params.append("password", motDePasse);

  const reponse = await api.post("/auth/connexion", params, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });

  // Stocker le jeton dans le navigateur
  const token = reponse.data.access_token;
  localStorage.setItem("token", token);
  return token;
}

// Récupérer les informations de l'utilisateur connecté
export async function utilisateurCourant() {
  const reponse = await api.get("/auth/moi");
  return reponse.data;
}

// Déconnexion : supprime le jeton
export function seDeconnecter() {
  localStorage.removeItem("token");
}
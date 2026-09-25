import api from "./api";

// Lister les utilisateurs (admin)
export async function getUtilisateurs() {
  const reponse = await api.get("/auth/utilisateurs");
  return reponse.data;
}

// Créer un utilisateur
export async function creerUtilisateur(donnees) {
  const reponse = await api.post("/auth/utilisateurs", donnees);
  return reponse.data;
}

// Modifier un utilisateur
export async function modifierUtilisateur(id, donnees) {
  const reponse = await api.put(`/auth/utilisateurs/${id}`, donnees);
  return reponse.data;
}

// Supprimer un utilisateur
export async function supprimerUtilisateur(id) {
  await api.delete(`/auth/utilisateurs/${id}`);
}
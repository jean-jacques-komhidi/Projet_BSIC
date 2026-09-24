import api from "./api";

// Lister tous les clients
export async function getClients() {
  const reponse = await api.get("/clients");
  return reponse.data;
}

// Rechercher des clients par nom
export async function rechercherClients(nom) {
  const reponse = await api.get("/clients/recherche", { params: { nom } });
  return reponse.data;
}

// Voir un client précis
export async function getClient(id) {
  const reponse = await api.get(`/clients/${id}`);
  return reponse.data;
}

// Créer un client
export async function creerClient(donnees) {
  const reponse = await api.post("/clients", donnees);
  return reponse.data;
}

// Modifier un client
export async function modifierClient(id, donnees) {
  const reponse = await api.put(`/clients/${id}`, donnees);
  return reponse.data;
}

// Supprimer un client (admin)
export async function supprimerClient(id) {
  await api.delete(`/clients/${id}`);
}
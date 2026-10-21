import api from "./api";

// Recherche globale (barre du haut) : clients et analyses
export async function rechercher(q) {
  const reponse = await api.get("/recherche", { params: { q } });
  return reponse.data;
}

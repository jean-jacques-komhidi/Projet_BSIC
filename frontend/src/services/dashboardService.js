import api from "./api";

// Récupère les statistiques du tableau de bord
export async function getTableauDeBord() {
  const reponse = await api.get("/dashboard");
  return reponse.data;
}
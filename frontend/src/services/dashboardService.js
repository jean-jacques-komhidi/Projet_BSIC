import api from "./api";

// Récupère les statistiques du tableau de bord sur une période : "7j", "30j" ou "tout"
export async function getTableauDeBord(periode = "30j") {
  const reponse = await api.get("/dashboard", { params: { periode } });
  return reponse.data;
}

import api from "./api";

// Lancer l'analyse de dérive
export async function analyserDerive() {
  const reponse = await api.get("/drift");
  return reponse.data;
}
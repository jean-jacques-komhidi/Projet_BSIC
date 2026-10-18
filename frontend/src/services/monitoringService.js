import api from "./api";

// État complet du modèle : données, prédictions, performance réelle, règle, versions
export async function getEtatModele() {
  const reponse = await api.get("/monitoring/etat");
  return reponse.data;
}

// Runs MLflow (modèles entraînés et leurs performances)
export async function getMlflowRuns() {
  const reponse = await api.get("/monitoring/mlflow");
  return reponse.data;
}

// Lancer le réentraînement (en tâche de fond)
export async function lancerRetrain() {
  const reponse = await api.post("/monitoring/retrain");
  return reponse.data;
}

// Progression du réentraînement
export async function getRetrainStatus() {
  const reponse = await api.get("/monitoring/retrain/status");
  return reponse.data;
}

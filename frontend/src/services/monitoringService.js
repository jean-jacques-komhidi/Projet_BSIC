import api from "./api";

// Les runs MLflow
export async function getMlflowRuns() {
  const reponse = await api.get("/monitoring/mlflow");
  return reponse.data;
}

// Lancer le réentraînement
export async function lancerRetrain() {
  const reponse = await api.post("/monitoring/retrain");
  return reponse.data;
}

// État du réentraînement
export async function getRetrainStatus() {
  const reponse = await api.get("/monitoring/retrain/status");
  return reponse.data;
}

// Analyse de la dérive
export async function getDrift() {
  const reponse = await api.get("/monitoring/drift");
  return reponse.data;
}
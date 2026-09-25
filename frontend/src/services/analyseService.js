import api from "./api";

// Réaliser et enregistrer une analyse
export async function realiserAnalyse(clientId, dossier) {
  const reponse = await api.post("/analyses", {
    client_id: clientId,
    dossier: dossier,
  });
  return reponse.data;
}

// Récupérer l'URL du PDF d'une analyse (pour le téléchargement)
export function getUrlPdf(analyseId) {
  return `/analyses/${analyseId}/pdf`;
}

// Télécharger le PDF d'une analyse
export async function telechargerPdf(analyseId) {
  const reponse = await api.get(`/analyses/${analyseId}/pdf`, {
    responseType: "blob",
  });
  return reponse.data;
}

// Lister toutes les analyses
export async function getAnalyses() {
  const reponse = await api.get("/analyses");
  return reponse.data;
}

// Voir une analyse précise (avec ses facteurs)
export async function getAnalyse(id) {
  const reponse = await api.get(`/analyses/${id}`);
  return reponse.data;
}

// Renseigner le résultat réel d'une analyse (admin)
export async function renseignerResultat(analyseId, resultat) {
  const reponse = await api.put(`/analyses/${analyseId}/resultat`, null, {
    params: { resultat },
  });
  return reponse.data;
}
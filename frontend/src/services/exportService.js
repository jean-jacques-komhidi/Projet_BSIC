import api from "./api";

// Groupes de colonnes, destinataires et nombre de lignes par jeu de données
export async function getOptionsExport() {
  const reponse = await api.get("/export/options");
  return reponse.data;
}

// Aperçu : 5 premières lignes et nombre total, selon les options choisies
export async function getApercu(options) {
  const reponse = await api.post("/export/apercu", options);
  return reponse.data;
}

// Téléchargement du fichier (CSV dans un .zip avec le dictionnaire, ou Excel)
export async function telechargerExport(demande) {
  const reponse = await api.post("/export/telecharger", demande, { responseType: "blob" });
  const entete = reponse.headers["content-disposition"] || "";
  const nom = (entete.match(/filename="([^"]+)"/) || [])[1] || `crediscore_${demande.jeu}.${demande.format === "xlsx" ? "xlsx" : "zip"}`;
  return { fichier: reponse.data, nom };
}

// Journal des derniers exports
export async function getJournalExports() {
  const reponse = await api.get("/export/journal");
  return reponse.data;
}

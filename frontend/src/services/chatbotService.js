import api from "./api";

// Lister les conversations de l'utilisateur
export async function getConversations() {
  const reponse = await api.get("/conversations");
  return reponse.data;
}

// Créer une nouvelle conversation
export async function creerConversation() {
  const reponse = await api.post("/conversations");
  return reponse.data;
}

// Lire une conversation (avec ses messages)
export async function getConversation(id) {
  const reponse = await api.get(`/conversations/${id}`);
  return reponse.data;
}

// Envoyer un message dans une conversation
export async function envoyerMessage(convId, question, analyseId = null) {
  const reponse = await api.post(`/conversations/${convId}/message`, {
    question: question,
    analyse_id: analyseId,
  });
  return reponse.data;
}

// Supprimer une conversation
export async function supprimerConversation(id) {
  await api.delete(`/conversations/${id}`);
}
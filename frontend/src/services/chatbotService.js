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

// Envoyer un message et recevoir la réponse progressivement (streaming).
// surMorceau(texteComplet) est appelé à chaque nouveau morceau reçu, avec tout
// le texte reçu jusque-là. Renvoie le texte final.
// (axios ne sait pas lire un flux dans le navigateur : on utilise fetch.)
export async function envoyerMessageFlux(convId, question, analyseId, surMorceau) {
  const token = localStorage.getItem("token");
  const reponse = await fetch(`${api.defaults.baseURL}/conversations/${convId}/message/flux`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question, analyse_id: analyseId }),
  });
  if (reponse.status === 401) localStorage.removeItem("token");
  if (!reponse.ok || !reponse.body) throw new Error(`Erreur ${reponse.status}`);

  const lecteur = reponse.body.getReader();
  const decodeur = new TextDecoder("utf-8");
  let texte = "";
  for (;;) {
    const { done, value } = await lecteur.read();
    if (done) break;
    texte += decodeur.decode(value, { stream: true });
    surMorceau(texte);
  }
  texte += decodeur.decode();
  surMorceau(texte);
  return texte;
}

// Supprimer une conversation
export async function supprimerConversation(id) {
  await api.delete(`/conversations/${id}`);
}
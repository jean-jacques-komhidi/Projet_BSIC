import api from "./api";

export async function getNotifications() {
  const reponse = await api.get("/notifications");
  return reponse.data;
}

export async function getNonLues() {
  const reponse = await api.get("/notifications/non-lues");
  return reponse.data.non_lues;
}

export async function marquerLue(id) {
  await api.put(`/notifications/${id}/lue`);
}

export async function toutMarquerLu() {
  await api.put("/notifications/tout-lu");
}
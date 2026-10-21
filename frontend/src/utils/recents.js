// Éléments consultés récemment (recherche de la barre du haut).
// Commodité propre à ce navigateur : rien n'est envoyé au serveur.
const CLE = "crediscore_recents";
const MAX = 5;

export function lireRecents() {
  try {
    const liste = JSON.parse(localStorage.getItem(CLE) || "[]");
    return Array.isArray(liste) ? liste : [];
  } catch {
    return [];
  }
}

export function ajouterRecent(element) {
  try {
    const cle = `${element.type}-${element.id}`;
    const liste = lireRecents().filter((e) => `${e.type}-${e.id}` !== cle);
    liste.unshift({ ...element, quand: Date.now() });
    localStorage.setItem(CLE, JSON.stringify(liste.slice(0, MAX)));
  } catch {
    /* stockage indisponible : on ignore */
  }
}

export function depuis(quand) {
  const minutes = Math.round((Date.now() - quand) / 60000);
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  const heures = Math.round(minutes / 60);
  if (heures < 24) return `il y a ${heures} h`;
  const jours = Math.round(heures / 24);
  return jours === 1 ? "hier" : `il y a ${jours} jours`;
}

export const reference = (a) => `CRED-${new Date(a.date_analyse || Date.now()).getFullYear()}-${String(a.id).padStart(4, "0")}`;

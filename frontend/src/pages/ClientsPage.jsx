import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import Header from "../components/ui/Header";
import ConfirmationSuppression from "../components/ui/ConfirmationSuppression";
import PiedDeListe from "../components/ui/PiedDeListe";
import useDefilementInfini from "../hooks/useDefilementInfini";
import { getSyntheseClients, creerClient, modifierClient, supprimerClient } from "../services/clientService";
import {
  Search, Plus, Pencil, Trash2, X, Loader2, FilePlus2, CheckCircle2,
} from "lucide-react";

// Couleurs de l'application : chaque couleur garde un seul sens
const BLEU = "#2E86C1", VERT = "#0F6E56", ORANGE = "#d97706", ROUGE = "#c0392b";
const CLAIR = { [VERT]: "#34d399", [ORANGE]: "#fbbf24", [ROUGE]: "#f87171", [BLEU]: "#7cc0ea" };
const PAS = 20;   // lignes ajoutées à chaque chargement

// Les VALEURS restent en anglais (attendues par le modèle / stockées en base),
// seuls les LIBELLÉS affichés sont en français.
const SITUATIONS = [
  { valeur: "Married", label: "Marié(e)" },
  { valeur: "Single / not married", label: "Célibataire" },
  { valeur: "Widow", label: "Veuf(ve)" },
  { valeur: "Separated", label: "Séparé(e) / divorcé(e)" },
  { valeur: "Civil marriage", label: "Union libre" },
];
const labelSituation = (valeur) => SITUATIONS.find((x) => x.valeur === valeur)?.label || valeur || "";

const versDate = (d) => new Date(String(d).endsWith("Z") ? d : d + "Z");
const dateCourte = (d) => versDate(d).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "Africa/Ndjamena" });
const pct = (p) => Math.round(p * 100) + " %";
const teinte = (p) => (p < 0.4 ? VERT : p < 0.7 ? ORANGE : ROUGE);
const sansAccent = (t) => (t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export default function ClientsPage() {
  const { isDark } = useTheme();
  const { utilisateur } = useAuth();
  const navigate = useNavigate();
  const estAdmin = utilisateur?.role === "admin";

  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur] = useState("");
  const [message, setMessage] = useState("");
  const [recherche, setRecherche] = useState("");
  const [modale, setModale] = useState({ ouverte: false, client: null });
  const [aSupprimer, setASupprimer] = useState(null);
  const [suppression, setSuppression] = useState({ enCours: false, erreur: "" });

  function charger() {
    return getSyntheseClients()
      .then((c) => { setClients(c); setErreur(""); })
      .catch(() => setErreur("Impossible de charger les clients. Vérifiez la connexion, puis actualisez la page."))
      .finally(() => setLoading(false));
  }
  useEffect(() => { charger(); }, []);

  const filtres = useMemo(() => {
    const mot = sansAccent(recherche.trim());
    return clients
      .filter((c) => !mot || sansAccent(c.nom).includes(mot) || sansAccent(c.profession).includes(mot))
      .sort((a, b) => a.nom.localeCompare(b.nom, "fr"));
  }, [clients, recherche]);

  const [nbAffiches, repere, chargementSuite, reinitialiser] = useDefilementInfini(filtres.length, PAS);
  const visibles = filtres.slice(0, nbAffiches);

  async function confirmerSuppression() {
    setSuppression({ enCours: true, erreur: "" });
    try {
      await supprimerClient(aSupprimer.id);
      setClients((l) => l.filter((c) => c.id !== aSupprimer.id));
      setMessage(`Le client ${aSupprimer.nom} a été supprimé.`);
      setASupprimer(null);
      setSuppression({ enCours: false, erreur: "" });
    } catch (e) {
      setSuppression({ enCours: false, erreur: e?.response?.data?.detail || "Suppression impossible. Réessayez." });
    }
  }

  const s = {
    carte: "rounded-2xl border " + (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm"),
    th: "py-2.5 pr-4 text-[11px] font-medium text-left whitespace-nowrap " + (isDark ? "text-zinc-500" : "text-gray-400"),
    td: "py-3 text-xs " + (isDark ? "text-zinc-300" : "text-gray-600"),
    libelle: "text-xs " + (isDark ? "text-zinc-500" : "text-gray-400"),
    bordure: isDark ? "border-zinc-800" : "border-gray-100",
    champ: "rounded-lg border outline-none focus:ring-2 focus:ring-[#2E86C1]/40 text-sm " +
      (isDark ? "bg-zinc-900 border-zinc-800 text-white" : "bg-white border-gray-200 text-gray-800"),
    icone: "inline-flex w-7 h-7 items-center justify-center rounded-lg border transition " +
      (isDark ? "border-zinc-700 text-zinc-400 hover:bg-zinc-800" : "border-gray-200 text-gray-500 hover:bg-gray-50"),
  };

  return (
    <div>
      <Header title="Clients" subtitle="Gestion des demandeurs de crédit" />

      {/* Recherche à gauche, création à droite */}
      <div className="flex items-center justify-between gap-3 mb-5">
        <div className="relative w-full max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input value={recherche} onChange={(e) => { setRecherche(e.target.value); reinitialiser(); }}
            placeholder="Rechercher un client par nom ou profession" aria-label="Rechercher un client"
            className={s.champ + " w-full pl-9 pr-3 py-2.5"} />
        </div>
        <button onClick={() => setModale({ ouverte: true, client: null })}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium text-white transition hover:opacity-90 shrink-0"
          style={{ backgroundColor: BLEU }}>
          <Plus size={16} /> Nouveau client
        </button>
      </div>

      {message && (
        <div role="status" className="mb-4 flex items-center gap-2 rounded-xl border px-4 py-3 text-sm"
          style={{ borderColor: VERT + "55", color: isDark ? CLAIR[VERT] : VERT, backgroundColor: VERT + (isDark ? "1f" : "0d") }}>
          <CheckCircle2 size={16} /> <span className="flex-1">{message}</span>
          <button onClick={() => setMessage("")} aria-label="Fermer le message"><X size={15} /></button>
        </div>
      )}
      {erreur && (
        <div className="mb-4 rounded-xl border px-4 py-3 text-sm"
          style={{ borderColor: ROUGE + "55", color: ROUGE, backgroundColor: ROUGE + "0d" }}>{erreur}</div>
      )}

      <div className={s.carte + " overflow-hidden"}>
        {loading ? (
          <div className="text-center py-12"><Loader2 size={26} className={"animate-spin mx-auto " + (isDark ? "text-zinc-600" : "text-gray-300")} /></div>
        ) : filtres.length === 0 ? (
          <div className="text-center py-12">
            <p className={"text-sm " + (isDark ? "text-zinc-400" : "text-gray-500")}>
              {clients.length === 0 ? "Aucun client pour l'instant." : `Aucun client ne correspond à « ${recherche} ».`}
            </p>
            {clients.length === 0 ? (
              <button onClick={() => setModale({ ouverte: true, client: null })} className="mt-3 text-sm font-medium" style={{ color: BLEU }}>
                Créer le premier client
              </button>
            ) : (
              <button onClick={() => { setRecherche(""); reinitialiser(); }} className="mt-3 text-sm font-medium" style={{ color: BLEU }}>
                Effacer la recherche
              </button>
            )}
          </div>
        ) : (
          <>
            <div className={"flex items-center gap-3 px-4 lg:px-5 py-4 border-b " + s.bordure}>
              <h2 className={"font-semibold text-sm " + (isDark ? "text-white" : "text-gray-800")}>Liste des clients</h2>
              <span className={"ml-auto text-xs px-2.5 py-1 rounded-full border " + (isDark ? "border-zinc-800 text-zinc-500" : "border-gray-200 text-gray-400")}>
                {filtres.length}
              </span>
            </div>
            <div className="overflow-x-auto px-4 lg:px-5">
              <table className="w-full min-w-[760px]">
                <thead><tr>
                  <th className={s.th}>Client</th>
                  <th className={s.th}>Situation familiale</th>
                  <th className={s.th + " text-center"}>Analyses</th>
                  <th className={s.th}>Dernière analyse</th>
                  <th className={s.th}>Dernier risque</th>
                  <th className={s.th + " pr-0"}><span className="sr-only">Actions</span></th>
                </tr></thead>
                <tbody>
                  {visibles.map((c) => {
                    const d = c.derniere_analyse;
                    const initiales = c.nom.split(" ").map((m) => m[0]).slice(0, 2).join("").toUpperCase();
                    const profil = [c.age ? Math.round(c.age) + " ans" : null, c.profession?.toLowerCase()].filter(Boolean).join(", ");
                    return (
                      <tr key={c.id} onClick={() => d && navigate(`/analyse/${d.id}`)} title={d ? "Ouvrir la dernière analyse" : undefined}
                        className={"border-t transition-colors " + s.bordure + " " + (d ? "cursor-pointer " + (isDark ? "hover:bg-zinc-800/40" : "hover:bg-gray-50") : "")}>
                        <td className="py-3 pr-4">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-lg grid place-items-center text-xs font-semibold shrink-0"
                              style={{ background: BLEU + (isDark ? "33" : "1a"), color: isDark ? CLAIR[BLEU] : BLEU }}>{initiales}</div>
                            <div>
                              <p className={"text-sm font-medium " + (isDark ? "text-zinc-100" : "text-gray-800")}>{c.nom}</p>
                              <p className={s.libelle}>{profil || "Profil incomplet"}</p>
                            </div>
                          </div>
                        </td>
                        <td className={s.td + " pr-4"}>{labelSituation(c.situation_familiale) || "—"}</td>
                        <td className={s.td + " text-center pr-4"}>{c.nb_analyses || "—"}</td>
                        <td className={s.td + " pr-4 whitespace-nowrap"}>
                          {d ? dateCourte(d.date) : <span className={isDark ? "text-zinc-500" : "text-gray-400"}>Jamais analysé</span>}
                        </td>
                        <td className="py-3 pr-4 whitespace-nowrap">
                          {d ? (
                            <span className="text-sm font-semibold" style={{ color: isDark ? CLAIR[teinte(d.probabilite_defaut)] : teinte(d.probabilite_defaut) }}>
                              {pct(d.probabilite_defaut)}
                              <span className={"ml-2 text-xs font-normal " + (isDark ? "text-zinc-500" : "text-gray-400")}>
                                {d.decision === "ACCORDE" ? "accordé" : "refusé"}
                              </span>
                            </span>
                          ) : <span className={isDark ? "text-zinc-600" : "text-gray-300"}>—</span>}
                        </td>
                        <td className="py-3 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                          <div className="inline-flex gap-1.5">
                            <button onClick={() => navigate(`/analyse?client=${c.id}`)} className={s.icone}
                              aria-label={`Nouvelle analyse pour ${c.nom}`} title="Nouvelle analyse">
                              <FilePlus2 size={14} />
                            </button>
                            <button onClick={() => setModale({ ouverte: true, client: c })} className={s.icone}
                              aria-label={`Modifier ${c.nom}`} title="Modifier le client">
                              <Pencil size={13} />
                            </button>
                            {estAdmin && (
                              <button onClick={() => { setSuppression({ enCours: false, erreur: "" }); setASupprimer(c); }}
                                aria-label={`Supprimer ${c.nom}`} title="Supprimer le client"
                                className={s.icone + (isDark ? " hover:text-red-400" : " hover:text-red-700")}>
                                <Trash2 size={13} />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <PiedDeListe affiches={nbAffiches} total={filtres.length} nom="clients"
              repere={repere} chargement={chargementSuite} isDark={isDark} />
          </>
        )}
      </div>

      {modale.ouverte && (
        <ModaleClient client={modale.client} isDark={isDark}
          onFermer={() => setModale({ ouverte: false, client: null })}
          onSauvegarde={(nom, nouveau) => {
            setModale({ ouverte: false, client: null });
            setMessage(nouveau ? `Le client ${nom} a été créé.` : `Le client ${nom} a été modifié.`);
            charger();
          }} />
      )}

      <ConfirmationSuppression
        ouverte={!!aSupprimer} enCours={suppression.enCours} erreur={suppression.erreur}
        bloque={!!aSupprimer?.nb_analyses}
        titre={aSupprimer ? (aSupprimer.nb_analyses ? `Impossible de supprimer ${aSupprimer.nom}` : `Supprimer le client ${aSupprimer.nom} ?`) : ""}
        details={aSupprimer ? [`Analyses : ${aSupprimer.nb_analyses}`,
          aSupprimer.derniere_analyse ? `Dernière analyse : ${dateCourte(aSupprimer.derniere_analyse.date)}` : "Jamais analysé"] : []}
        avertissement={aSupprimer?.nb_analyses
          ? "Un client qui a des analyses ne peut pas être supprimé : ses décisions de crédit doivent rester traçables. Supprimez d'abord ses analyses depuis l'historique."
          : "La suppression est définitive."}
        onConfirmer={confirmerSuppression} onAnnuler={() => setASupprimer(null)} />
    </div>
  );
}

function ModaleClient({ client, isDark, onFermer, onSauvegarde }) {
  const [form, setForm] = useState({
    nom: client?.nom || "",
    genre: client?.genre || "M",
    age: client?.age ? Math.round(client.age) : "",
    profession: client?.profession || "",
    situation_familiale: client?.situation_familiale || "Married",
  });
  const [erreur, setErreur] = useState("");
  const [chargement, setChargement] = useState(false);

  useEffect(() => {
    const touche = (e) => { if (e.key === "Escape" && !chargement) onFermer(); };
    window.addEventListener("keydown", touche);
    return () => window.removeEventListener("keydown", touche);
  }, [chargement, onFermer]);

  const maj = (champ, valeur) => setForm((f) => ({ ...f, [champ]: valeur }));

  async function sauvegarder(e) {
    e.preventDefault();
    setErreur("");
    setChargement(true);
    try {
      const donnees = { ...form, nom: form.nom.trim(), age: form.age ? parseFloat(form.age) : null };
      if (client) await modifierClient(client.id, donnees);
      else await creerClient(donnees);
      onSauvegarde(donnees.nom, !client);
    } catch {
      setErreur("Enregistrement impossible. Vérifiez le nom et l'âge (entre 18 et 100 ans).");
    } finally {
      setChargement(false);
    }
  }

  const champ = "w-full px-3 py-2 rounded-lg border outline-none focus:ring-2 focus:ring-[#2E86C1]/40 text-sm " +
    (isDark ? "bg-zinc-800 border-zinc-700 text-white" : "bg-white border-gray-200 text-gray-800");
  const etiquette = "block text-sm font-medium mb-1 " + (isDark ? "text-zinc-300" : "text-gray-700");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="titre-client">
      <div className="absolute inset-0 bg-black/40" onClick={() => !chargement && onFermer()} />
      <div className={"relative w-full max-w-md rounded-2xl border p-6 shadow-xl " + (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100")}>
        <div className="flex items-start justify-between mb-5">
          <div>
            <h2 id="titre-client" className={"font-semibold " + (isDark ? "text-white" : "text-gray-800")}>
              {client ? "Modifier le client" : "Nouveau client"}
            </h2>
            <p className={"text-xs mt-0.5 " + (isDark ? "text-zinc-500" : "text-gray-400")}>
              Identité du demandeur. Les revenus et le crédit se saisissent lors de l'analyse.
            </p>
          </div>
          <button onClick={onFermer} aria-label="Fermer" className={isDark ? "text-zinc-500" : "text-gray-400"}><X size={20} /></button>
        </div>

        <form onSubmit={sauvegarder} className="space-y-3">
          <div>
            <label htmlFor="client-nom" className={etiquette}>Nom complet</label>
            <input id="client-nom" value={form.nom} onChange={(e) => maj("nom", e.target.value)} required autoFocus className={champ} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="client-genre" className={etiquette}>Genre</label>
              <select id="client-genre" value={form.genre} onChange={(e) => maj("genre", e.target.value)} className={champ}>
                <option value="M">Masculin</option>
                <option value="F">Féminin</option>
              </select>
            </div>
            <div>
              <label htmlFor="client-age" className={etiquette}>Âge</label>
              <input id="client-age" type="number" value={form.age} onChange={(e) => maj("age", e.target.value)} className={champ} min="18" max="100" />
            </div>
          </div>
          <div>
            <label htmlFor="client-profession" className={etiquette}>Profession</label>
            <input id="client-profession" value={form.profession} onChange={(e) => maj("profession", e.target.value)} className={champ} />
          </div>
          <div>
            <label htmlFor="client-situation" className={etiquette}>Situation familiale</label>
            <select id="client-situation" value={form.situation_familiale} onChange={(e) => maj("situation_familiale", e.target.value)} className={champ}>
              {SITUATIONS.map((x) => <option key={x.valeur} value={x.valeur}>{x.label}</option>)}
            </select>
          </div>

          {erreur && <p className="text-sm" style={{ color: ROUGE }}>{erreur}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onFermer}
              className={"px-4 py-2 rounded-lg text-sm font-medium border " + (isDark ? "border-zinc-700 text-zinc-300 hover:bg-zinc-800" : "border-gray-200 text-gray-700 hover:bg-gray-50")}>
              Annuler
            </button>
            <button type="submit" disabled={chargement}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-60" style={{ backgroundColor: BLEU }}>
              {chargement && <Loader2 size={15} className="animate-spin" />} {client ? "Enregistrer" : "Créer le client"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

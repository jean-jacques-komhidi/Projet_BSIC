import { useState, useEffect } from "react";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import Header from "../components/ui/Header";
import {
  getClients, rechercherClients, creerClient, modifierClient, supprimerClient,
} from "../services/clientService";
import {
  Users, Search, Plus, Pencil, Trash2, X, Loader2,
} from "lucide-react";

const SITUATIONS = ["Married", "Single / not married", "Widow", "Separated"];

export default function ClientsPage() {
  const { isDark } = useTheme();
  const { utilisateur } = useAuth();
  const estAdmin = utilisateur?.role === "admin";

  const [clients, setClients] = useState([]);
  const [recherche, setRecherche] = useState("");
  const [loading, setLoading] = useState(true);
  const [modaleOuverte, setModaleOuverte] = useState(false);
  const [clientEnCours, setClientEnCours] = useState(null);

  async function charger() {
    setLoading(true);
    try { setClients(await getClients()); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }
  useEffect(() => { charger(); }, []);

  useEffect(() => {
    const t = setTimeout(async () => {
      if (recherche.trim()) {
        try { setClients(await rechercherClients(recherche)); } catch {}
      } else {
        charger();
      }
    }, 400);
    return () => clearTimeout(t);
  }, [recherche]);

  function ouvrirCreation() {
    setClientEnCours(null);
    setModaleOuverte(true);
  }
  function ouvrirModification(client) {
    setClientEnCours(client);
    setModaleOuverte(true);
  }

  async function supprimer(client) {
    if (!confirm(`Supprimer le client ${client.nom} ?`)) return;
    try {
      await supprimerClient(client.id);
      charger();
    } catch {
      alert("Suppression impossible.");
    }
  }

  const cardClass = "rounded-2xl border overflow-hidden " +
    (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");
  const headClass = "text-xs uppercase tracking-wider " + (isDark ? "text-zinc-600" : "text-gray-400");
  const cellClass = "py-3 text-sm " + (isDark ? "text-zinc-300" : "text-gray-600");
  const borderB = isDark ? "border-zinc-800" : "border-gray-100";

  return (
    <div>
      <Header title="Clients" subtitle="Gestion des demandeurs de crédit" />

      {/* Barre d'actions : recherche à gauche, bouton à droite */}
      <div className="flex items-center justify-between gap-3 mb-5">
        <div className="relative w-full max-w-md">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={recherche}
            onChange={(e) => setRecherche(e.target.value)}
            placeholder="Rechercher un client par nom..."
            className={"w-full pl-10 pr-4 py-2.5 rounded-lg border outline-none focus:ring-2 focus:ring-blue-500 text-sm " +
              (isDark ? "bg-zinc-900 border-zinc-800 text-white" : "bg-white border-gray-200 text-gray-800")}
          />
        </div>
        <button
          onClick={ouvrirCreation}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium text-white transition hover:opacity-90 shrink-0"
          style={{ backgroundColor: "#2E86C1" }}
        >
          <Plus size={16} /> Nouveau client
        </button>
      </div>

      {/* Tableau des clients */}
      <div className={cardClass}>
        <div className={"flex items-center gap-3 p-4 lg:p-5 border-b " + borderB}>
          <Users size={16} className={isDark ? "text-zinc-500" : "text-gray-400"} />
          <h2 className={"font-semibold text-sm " + (isDark ? "text-white" : "text-gray-800")}>
            Liste des clients
          </h2>
          <span className={"ml-auto text-xs px-2.5 py-1 rounded-full border " +
            (isDark ? "border-zinc-800 text-zinc-500" : "border-gray-200 text-gray-400")}>
            {clients.length}
          </span>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <Loader2 size={26} className={"animate-spin mx-auto " + (isDark ? "text-zinc-600" : "text-gray-300")} />
          </div>
        ) : clients.length === 0 ? (
          <p className={"text-center py-12 text-sm " + (isDark ? "text-zinc-500" : "text-gray-400")}>
            Aucun client trouvé.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-150">
              <thead>
                <tr className={"border-b " + borderB}>
                  <th className={"text-left py-3 px-4 lg:px-5 " + headClass}>Nom</th>
                  <th className={"text-center py-3 " + headClass}>Genre</th>
                  <th className={"text-center py-3 " + headClass}>Âge</th>
                  <th className={"text-left py-3 " + headClass}>Profession</th>
                  <th className={"text-left py-3 " + headClass}>Situation</th>
                  <th className={"text-right py-3 pr-4 lg:pr-5 " + headClass}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {clients.map((c) => (
                  <tr key={c.id} className={"border-t transition-colors " +
                    (isDark ? "border-zinc-800/50 hover:bg-zinc-800/30" : "border-gray-50 hover:bg-gray-50/80")}>
                    <td className={cellClass + " px-4 lg:px-5 font-medium " + (isDark ? "text-white" : "text-gray-800")}>{c.nom}</td>
                    <td className={cellClass + " text-center"}>{c.genre || "—"}</td>
                    <td className={cellClass + " text-center"}>{c.age ? Math.round(c.age) + " ans" : "—"}</td>
                    <td className={cellClass}>{c.profession || "—"}</td>
                    <td className={cellClass}>{c.situation_familiale || "—"}</td>
                    <td className="py-3 text-right pr-4 lg:pr-5">
                      <div className="flex items-center justify-end gap-2">
                        <button onClick={() => ouvrirModification(c)}
                          className={"p-1.5 rounded-lg transition " + (isDark ? "hover:bg-zinc-800 text-zinc-400" : "hover:bg-gray-100 text-gray-500")}>
                          <Pencil size={15} />
                        </button>
                        {estAdmin && (
                          <button onClick={() => supprimer(c)}
                            className="p-1.5 rounded-lg transition hover:bg-red-50 text-red-500">
                            <Trash2 size={15} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modaleOuverte && (
        <ModaleClient
          client={clientEnCours}
          isDark={isDark}
          onFermer={() => setModaleOuverte(false)}
          onSauvegarde={() => { setModaleOuverte(false); charger(); }}
        />
      )}
    </div>
  );
}

function ModaleClient({ client, isDark, onFermer, onSauvegarde }) {
  const [form, setForm] = useState({
    nom: client?.nom || "",
    genre: client?.genre || "M",
    age: client?.age || "",
    profession: client?.profession || "",
    situation_familiale: client?.situation_familiale || "Married",
  });
  const [erreur, setErreur] = useState("");
  const [chargement, setChargement] = useState(false);

  function maj(champ, valeur) {
    setForm((f) => ({ ...f, [champ]: valeur }));
  }

  async function sauvegarder(e) {
    e.preventDefault();
    setErreur("");
    setChargement(true);
    try {
      const donnees = { ...form, age: form.age ? parseFloat(form.age) : null };
      if (client) {
        await modifierClient(client.id, donnees);
      } else {
        await creerClient(donnees);
      }
      onSauvegarde();
    } catch {
      setErreur("Enregistrement impossible. Vérifiez les champs.");
    } finally {
      setChargement(false);
    }
  }

  const inputClass = "w-full px-3 py-2 rounded-lg border outline-none focus:ring-2 focus:ring-blue-500 text-sm " +
    (isDark ? "bg-zinc-800 border-zinc-700 text-white" : "bg-white border-gray-200 text-gray-800");
  const labelClass = "block text-sm font-medium mb-1 " + (isDark ? "text-zinc-300" : "text-gray-700");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className={"w-full max-w-md rounded-2xl p-6 " + (isDark ? "bg-zinc-900" : "bg-white")}>
        <div className="flex items-center justify-between mb-5">
          <h2 className={"font-bold " + (isDark ? "text-white" : "text-gray-800")}>
            {client ? "Modifier le client" : "Nouveau client"}
          </h2>
          <button onClick={onFermer} className={isDark ? "text-zinc-500" : "text-gray-400"}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={sauvegarder} className="space-y-3">
          <div>
            <label className={labelClass}>Nom complet</label>
            <input value={form.nom} onChange={(e) => maj("nom", e.target.value)} required className={inputClass} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Genre</label>
              <select value={form.genre} onChange={(e) => maj("genre", e.target.value)} className={inputClass}>
                <option value="M">Masculin</option>
                <option value="F">Féminin</option>
              </select>
            </div>
            <div>
              <label className={labelClass}>Âge</label>
              <input type="number" value={form.age} onChange={(e) => maj("age", e.target.value)} className={inputClass} min="18" max="100" />
            </div>
          </div>
          <div>
            <label className={labelClass}>Profession</label>
            <input value={form.profession} onChange={(e) => maj("profession", e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Situation familiale</label>
            <select value={form.situation_familiale} onChange={(e) => maj("situation_familiale", e.target.value)} className={inputClass}>
              {SITUATIONS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          {erreur && <p className="text-sm text-center text-red-500">{erreur}</p>}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onFermer}
              className={"flex-1 py-2.5 rounded-lg text-sm font-medium border " +
                (isDark ? "border-zinc-700 text-zinc-300" : "border-gray-200 text-gray-600")}>
              Annuler
            </button>
            <button type="submit" disabled={chargement}
              className="flex-1 py-2.5 rounded-lg text-sm font-medium text-white disabled:opacity-60"
              style={{ backgroundColor: "#2E86C1" }}>
              {chargement ? "..." : (client ? "Modifier" : "Créer")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
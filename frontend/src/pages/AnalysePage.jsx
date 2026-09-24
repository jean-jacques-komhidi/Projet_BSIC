import { useState, useRef } from "react";
import { useTheme } from "../context/ThemeContext";
import Header from "../components/ui/Header";
import ScoreForm from "../components/ScoreForm";
import ScoreResult from "../components/ScoreResult";
import ShapChart from "../components/ShapChart";
import { rechercherClients } from "../services/clientService";
import { realiserAnalyse, telechargerPdf } from "../services/analyseService";
import {
  Search, Loader2, ChevronRight, X, SearchX,
  User, Briefcase, Heart, Users as UsersIcon,
} from "lucide-react";

// ── RECHERCHE CLIENT ──
function ClientSearch({ isDark, onClientSelectionne }) {
  const [query, setQuery] = useState("");
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const timer = useRef(null);

  const handleSearch = (val) => {
    setQuery(val);
    clearTimeout(timer.current);
    if (val.length < 2) { setClients([]); setSearched(false); return; }
    timer.current = setTimeout(async () => {
      setLoading(true);
      try {
        setClients(await rechercherClients(val));
        setSearched(true);
      } catch { setClients([]); }
      finally { setLoading(false); }
    }, 400);
  };

  const inputClass = "w-full border rounded-xl px-4 py-3 text-sm pl-10 outline-none focus:ring-1 focus:ring-blue-500 " +
    (isDark ? "bg-zinc-800 border-zinc-700 text-white placeholder-zinc-500" : "bg-white border-gray-200 text-gray-800 placeholder-gray-400");
  const cardCli = "rounded-xl border p-3.5 cursor-pointer transition-all " +
    (isDark ? "bg-zinc-900 border-zinc-800 hover:border-zinc-600 hover:bg-zinc-800" : "bg-white border-gray-100 hover:border-gray-300 shadow-sm");

  const initiales = (c) => (c.nom || "?").split(" ").map((m) => m[0]).slice(0, 2).join("").toUpperCase();

  return (
    <div>
      <div className={"rounded-2xl border p-4 lg:p-5 mb-4 " + (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm")}>
        <div className="flex items-center gap-2.5 mb-4">
          <div className={"w-8 h-8 rounded-lg flex items-center justify-center " + (isDark ? "bg-zinc-800" : "bg-gray-100")}>
            <Search size={15} className={isDark ? "text-zinc-400" : "text-gray-500"} />
          </div>
          <div>
            <h3 className={"font-semibold text-sm " + (isDark ? "text-white" : "text-gray-800")}>Rechercher un client</h3>
            <p className={"text-xs " + (isDark ? "text-zinc-500" : "text-gray-400")}>Saisissez le nom du client</p>
          </div>
        </div>
        <div className="relative">
          <Search size={15} className={"absolute left-3.5 top-1/2 -translate-y-1/2 " + (isDark ? "text-zinc-500" : "text-gray-400")} />
          <input value={query} onChange={(e) => handleSearch(e.target.value)} placeholder="Ex : Kadidja, Ahmat..." className={inputClass} />
          {loading && <Loader2 size={15} className="absolute right-3.5 top-1/2 -translate-y-1/2 animate-spin text-gray-400" />}
        </div>
      </div>

      {searched && clients.length === 0 && (
        <div className={"text-center py-8 text-sm rounded-xl border-2 border-dashed " + (isDark ? "border-zinc-800 text-zinc-600" : "border-gray-200 text-gray-400")}>
          Aucun client trouvé pour « {query} »
        </div>
      )}

      <div className="space-y-2">
        {clients.map((c) => (
          <div key={c.id} className={cardCli} onClick={() => onClientSelectionne(c)}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={"w-9 h-9 rounded-full flex items-center justify-center font-semibold text-sm " +
                  (isDark ? "bg-zinc-800 text-zinc-300" : "bg-gray-100 text-gray-600")}>
                  {initiales(c)}
                </div>
                <div>
                  <p className={"font-medium text-sm " + (isDark ? "text-white" : "text-gray-800")}>{c.nom}</p>
                  <p className={"text-xs " + (isDark ? "text-zinc-500" : "text-gray-400")}>
                    {c.profession || "—"}{c.age ? " · " + Math.round(c.age) + " ans" : ""}
                  </p>
                </div>
              </div>
              <ChevronRight size={15} className={isDark ? "text-zinc-600" : "text-gray-300"} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── FICHE CLIENT SÉLECTIONNÉ (adaptée à nos champs) ──
function ClientCard({ client, isDark, onDeselect }) {
  const labelClass = "text-xs " + (isDark ? "text-zinc-500" : "text-gray-400");
  const valueClass = "text-sm font-medium " + (isDark ? "text-zinc-200" : "text-gray-700");
  const initiales = (client.nom || "?").split(" ").map((m) => m[0]).slice(0, 2).join("").toUpperCase();

  const infos = [
    [User, "Genre", client.genre === "M" ? "Masculin" : client.genre === "F" ? "Féminin" : "—"],
    [Heart, "Âge", client.age ? Math.round(client.age) + " ans" : "—"],
    [Briefcase, "Profession", client.profession || "—"],
    [UsersIcon, "Situation", client.situation_familiale || "—"],
  ];

  return (
    <div className={"rounded-xl border p-4 mb-4 " + (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm")}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={"w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm " +
            (isDark ? "bg-zinc-800 text-zinc-200" : "bg-gray-100 text-gray-600")}>
            {initiales}
          </div>
          <div>
            <p className={"font-semibold text-sm " + (isDark ? "text-white" : "text-gray-800")}>{client.nom}</p>
            <span className={"text-xs px-2 py-0.5 rounded-full border " + (isDark ? "border-zinc-700 text-zinc-400" : "border-gray-200 text-gray-500")}>
              Client #{client.id}
            </span>
          </div>
        </div>
        <button onClick={onDeselect} className={"p-1.5 rounded-lg " + (isDark ? "hover:bg-zinc-800 text-zinc-500" : "hover:bg-gray-100 text-gray-400")}>
          <X size={15} />
        </button>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {infos.map(([Icone, label, val], i) => (
          <div key={i} className="flex items-center gap-2">
            <Icone size={13} className={isDark ? "text-zinc-600" : "text-gray-400"} />
            <div>
              <p className={labelClass}>{label}</p>
              <p className={valueClass}>{val}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── PAGE PRINCIPALE ──
export default function AnalysePage() {
  const { isDark } = useTheme();
  const [clientSelectionne, setClientSelectionne] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [etape, setEtape] = useState("recherche");
  const resultRef = useRef(null);

  function selectionner(client) {
    setClientSelectionne(client);
    setEtape("analyse");
    setResult(null);
    setError(null);
  }
  function deselectionner() {
    setClientSelectionne(null);
    setEtape("recherche");
    setResult(null);
    setError(null);
  }

  async function analyser(dossier) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await realiserAnalyse(clientSelectionne.id, dossier);
      setResult(data);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
    } catch {
      setError("Analyse impossible. Vérifiez les champs du dossier.");
    } finally {
      setLoading(false);
    }
  }

  async function exporterPdf() {
    if (!result) return;
    try {
      const blob = await telechargerPdf(result.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `fiche_decision_${result.id}.pdf`; a.click();
      window.URL.revokeObjectURL(url);
    } catch { alert("Téléchargement du PDF impossible."); }
  }

  const emptyState = (
    <div className={"rounded-2xl border-2 border-dashed p-10 text-center " + (isDark ? "border-zinc-800" : "border-gray-200")}>
      <div className={"w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-3 " + (isDark ? "bg-zinc-800" : "bg-gray-100")}>
        <SearchX size={22} className={isDark ? "text-zinc-600" : "text-gray-400"} />
      </div>
      <p className={"font-medium text-sm " + (isDark ? "text-zinc-400" : "text-gray-500")}>
        {etape === "recherche" ? "Recherchez un client pour commencer" : "Remplissez le formulaire pour obtenir un résultat"}
      </p>
      <p className={"text-xs mt-1 " + (isDark ? "text-zinc-600" : "text-gray-400")}>
        {etape === "recherche" ? "Saisissez le nom du demandeur" : "Le modèle calculera le score de risque"}
      </p>
    </div>
  );

  return (
    <div>
      <Header title="Analyse de crédit" subtitle="Évaluez le risque de défaut d'un dossier" />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
        {/* Colonne gauche */}
        <div>
          {etape === "recherche" && <ClientSearch isDark={isDark} onClientSelectionne={selectionner} />}
          {etape === "analyse" && clientSelectionne && (
            <>
              <ClientCard client={clientSelectionne} isDark={isDark} onDeselect={deselectionner} />
              <ScoreForm onSubmit={analyser} loading={loading} client={clientSelectionne} />
            </>
          )}
        </div>

        {/* Colonne droite : résultat */}
        <div ref={resultRef} className="lg:sticky lg:top-5 space-y-4 lg:max-h-[calc(100vh-40px)] lg:overflow-y-auto">
          {error && (
            <div className={"rounded-xl border p-4 text-sm flex items-center gap-2 " +
              (isDark ? "bg-red-500/10 border-red-900 text-red-400" : "bg-red-50 border-red-200 text-red-700")}>
              <SearchX size={15} /> {error}
            </div>
          )}
          {!result && !loading && emptyState}
          {loading && (
            <div className={"rounded-2xl border p-10 text-center " + (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm")}>
              <Loader2 size={32} className="animate-spin text-blue-600 mx-auto mb-3" />
              <p className={"font-medium text-sm " + (isDark ? "text-zinc-300" : "text-gray-600")}>Analyse en cours...</p>
            </div>
          )}
          {result && (
            <>
              <ScoreResult result={result} onPdf={exporterPdf} />
              <ShapChart result={result} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
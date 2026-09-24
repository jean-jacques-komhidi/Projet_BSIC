import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import Header from "../components/ui/Header";
import { getAnalyses, telechargerPdf } from "../services/analyseService";
import { History, Loader2, FileDown, Eye, Search } from "lucide-react";

export default function HistoriquePage() {
  const { isDark } = useTheme();
  const navigate = useNavigate();
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtre, setFiltre] = useState("toutes");
  const [recherche, setRecherche] = useState("");

  async function charger() {
    setLoading(true);
    try { setAnalyses(await getAnalyses()); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }
  useEffect(() => { charger(); }, []);

  // Filtre par décision ET par recherche de nom
  const filtrees = analyses.filter((a) => {
    const okDecision = filtre === "toutes" || a.decision === filtre;
    const okRecherche = !recherche.trim() ||
      (a.nom_client && a.nom_client.toLowerCase().includes(recherche.toLowerCase()));
    return okDecision && okRecherche;
  });

  async function exporterPdf(id) {
    try {
      const blob = await telechargerPdf(id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `fiche_decision_${id}.pdf`; a.click();
      window.URL.revokeObjectURL(url);
    } catch { alert("Téléchargement impossible."); }
  }

  const cardClass = "rounded-2xl border overflow-hidden " +
    (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");
  const headClass = "text-xs uppercase tracking-wider " + (isDark ? "text-zinc-600" : "text-gray-400");
  const cellClass = "py-3 text-xs " + (isDark ? "text-zinc-300" : "text-gray-600");
  const borderB = isDark ? "border-zinc-800" : "border-gray-100";

  function BoutonFiltre({ valeur, label }) {
    const actif = filtre === valeur;
    return (
      <button onClick={() => setFiltre(valeur)}
        className={"px-3 py-1.5 rounded-lg text-xs font-medium transition border " +
          (actif
            ? "text-white border-transparent"
            : (isDark ? "border-zinc-800 text-zinc-400 hover:bg-zinc-800" : "border-gray-200 text-gray-500 hover:bg-gray-50"))}
        style={actif ? { backgroundColor: "#2E86C1" } : {}}>
        {label}
      </button>
    );
  }

  function badgeRisque(niveau) {
    const cfg = {
      faible: isDark ? "text-emerald-400 border-emerald-800" : "text-emerald-700 border-emerald-200",
      moyen: isDark ? "text-amber-400 border-amber-800" : "text-amber-700 border-amber-200",
      eleve: isDark ? "text-red-400 border-red-800" : "text-red-700 border-red-200",
    };
    return (
      <span className={"text-xs px-2 py-0.5 rounded-full border font-medium capitalize " +
        (cfg[niveau] || (isDark ? "text-zinc-400 border-zinc-700" : "text-gray-500 border-gray-200"))}>
        {niveau}
      </span>
    );
  }

  const formatDate = (d) => d
    ? new Date(d).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" })
    : "—";

  return (
    <div>
      <Header title="Historique des analyses" subtitle="Toutes les analyses réalisées" />

      {/* Barre : filtres à gauche, recherche à droite */}
      <div className="flex items-center justify-between gap-3 mb-5 flex-wrap">
        <div className="flex items-center gap-2">
          <BoutonFiltre valeur="toutes" label={`Toutes (${analyses.length})`} />
          <BoutonFiltre valeur="ACCORDE" label="Accordées" />
          <BoutonFiltre valeur="REFUSE" label="Refusées" />
        </div>
        <div className="relative w-full sm:w-64">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={recherche}
            onChange={(e) => setRecherche(e.target.value)}
            placeholder="Rechercher un client..."
            className={"w-full pl-9 pr-3 py-2 rounded-lg border outline-none focus:ring-2 focus:ring-blue-500 text-sm " +
              (isDark ? "bg-zinc-900 border-zinc-800 text-white" : "bg-white border-gray-200 text-gray-800")}
          />
        </div>
      </div>

      {/* Tableau */}
      <div className={cardClass}>
        <div className={"flex items-center gap-3 p-4 lg:p-5 border-b " + borderB}>
          <History size={16} className={isDark ? "text-zinc-500" : "text-gray-400"} />
          <h2 className={"font-semibold text-sm " + (isDark ? "text-white" : "text-gray-800")}>Analyses</h2>
          <span className={"ml-auto text-xs px-2.5 py-1 rounded-full border " +
            (isDark ? "border-zinc-800 text-zinc-500" : "border-gray-200 text-gray-400")}>
            {filtrees.length}
          </span>
        </div>

        {loading ? (
          <div className="text-center py-12"><Loader2 size={26} className={"animate-spin mx-auto " + (isDark ? "text-zinc-600" : "text-gray-300")} /></div>
        ) : filtrees.length === 0 ? (
          <p className={"text-center py-12 text-sm " + (isDark ? "text-zinc-500" : "text-gray-400")}>Aucune analyse trouvée.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-160">
              <thead>
                <tr className={"border-b " + borderB}>
                  <th className={"text-left py-3 px-4 lg:px-5 " + headClass}>Date</th>
                  <th className={"text-left py-3 " + headClass}>Client</th>
                  <th className={"text-center py-3 " + headClass}>Risque</th>
                  <th className={"text-right py-3 " + headClass}>Proba.</th>
                  <th className={"text-center py-3 " + headClass}>Décision</th>
                  <th className={"text-right py-3 pr-4 lg:pr-5 " + headClass}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtrees.map((a) => (
                  <tr key={a.id}
                    onClick={() => navigate(`/analyse/${a.id}`)}
                    className={"border-t transition-colors cursor-pointer " +
                    (isDark ? "border-zinc-800/50 hover:bg-zinc-800/30" : "border-gray-50 hover:bg-gray-50/80")}>
                    <td className={cellClass + " px-4 lg:px-5 whitespace-nowrap"}>{formatDate(a.date_analyse)}</td>
                    <td className="py-3">
                      <span className={"text-xs font-medium " + (isDark ? "text-zinc-200" : "text-gray-700")}>{a.nom_client || "—"}</span>
                    </td>
                    <td className="py-3 text-center">{badgeRisque(a.classe_risque)}</td>
                    <td className={"py-3 text-right text-xs font-medium " +
                      (a.probabilite_defaut > 0.7 ? "text-red-500" : "text-emerald-500")}>
                      {Math.round(a.probabilite_defaut * 100)}%
                    </td>
                    <td className="py-3 text-center">
                      <span className={"text-xs px-2 py-0.5 rounded-full font-medium border " +
                        (a.decision === "ACCORDE"
                          ? (isDark ? "text-emerald-400 border-emerald-800" : "text-emerald-700 border-emerald-200")
                          : (isDark ? "text-red-400 border-red-800" : "text-red-700 border-red-200"))}>
                        {a.decision === "ACCORDE" ? "Accordé" : "Refusé"}
                      </span>
                    </td>
                    <td className="py-3 text-right pr-4 lg:pr-5" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1.5">
                        <button onClick={() => navigate(`/analyse/${a.id}`)}
                          className={"p-1.5 rounded-lg transition " + (isDark ? "hover:bg-zinc-800 text-zinc-400" : "hover:bg-gray-100 text-gray-500")}>
                          <Eye size={15} />
                        </button>
                        <button onClick={() => exporterPdf(a.id)}
                          className={"p-1.5 rounded-lg transition " + (isDark ? "hover:bg-zinc-800 text-zinc-400" : "hover:bg-gray-100 text-gray-500")}>
                          <FileDown size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
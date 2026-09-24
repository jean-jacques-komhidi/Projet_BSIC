import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import ScoreResult from "../components/ScoreResult";
import ShapChart from "../components/ShapChart";
import { getAnalyse, telechargerPdf } from "../services/analyseService";
import { ArrowLeft, Loader2, Calendar, User, Hash } from "lucide-react";

export default function AnalyseDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isDark } = useTheme();
  const [analyse, setAnalyse] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAnalyse(id)
      .then(setAnalyse)
      .catch(() => setAnalyse(null))
      .finally(() => setLoading(false));
  }, [id]);

  async function exporterPdf() {
    try {
      const blob = await telechargerPdf(id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `fiche_decision_${id}.pdf`; a.click();
      window.URL.revokeObjectURL(url);
    } catch { alert("Téléchargement impossible."); }
  }

  const formatDate = (d) => d
    ? new Date(d).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" })
    : "—";

  const cardClass = "rounded-2xl border p-5 " +
    (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");

  if (loading) {
    return (
      <div className="pt-16 lg:pt-20 text-center py-20">
        <Loader2 size={30} className={"animate-spin mx-auto " + (isDark ? "text-zinc-600" : "text-gray-300")} />
      </div>
    );
  }

  if (!analyse) {
    return (
      <div className="pt-16 lg:pt-20 text-center py-20">
        <p className={isDark ? "text-zinc-400" : "text-gray-500"}>Analyse introuvable.</p>
        <button onClick={() => navigate("/historique")}
          className="mt-4 px-4 py-2 rounded-lg text-white text-sm" style={{ backgroundColor: "#2E86C1" }}>
          Retour à l'historique
        </button>
      </div>
    );
  }

  return (
    <div className="pt-16 lg:pt-20">
      {/* Barre supérieure : retour + titre */}
      <div className="flex items-center gap-3 mb-5">
        <button onClick={() => navigate("/historique")}
          className={"p-2 rounded-lg border transition " +
            (isDark ? "border-zinc-800 text-zinc-400 hover:bg-zinc-800" : "border-gray-200 text-gray-500 hover:bg-gray-50")}>
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className={"text-xl font-bold " + (isDark ? "text-white" : "text-gray-800")}>
            Analyse #{analyse.id}
          </h1>
          <p className={"text-xs " + (isDark ? "text-zinc-500" : "text-gray-400")}>
            Détail de la décision de crédit
          </p>
        </div>
      </div>

      {/* Infos rapides */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
        <div className={cardClass + " flex items-center gap-3"}>
          <div className="h-9 w-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: "#2E86C11a" }}>
            <User size={18} style={{ color: "#2E86C1" }} />
          </div>
          <div>
            <p className={"text-xs " + (isDark ? "text-zinc-500" : "text-gray-400")}>Client</p>
            <p className={"text-sm font-medium " + (isDark ? "text-white" : "text-gray-800")}>{analyse.nom_client || "—"}</p>
          </div>
        </div>
        <div className={cardClass + " flex items-center gap-3"}>
          <div className="h-9 w-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: "#0F6E561a" }}>
            <Hash size={18} style={{ color: "#0F6E56" }} />
          </div>
          <div>
            <p className={"text-xs " + (isDark ? "text-zinc-500" : "text-gray-400")}>Numéro</p>
            <p className={"text-sm font-medium " + (isDark ? "text-white" : "text-gray-800")}>#{analyse.id}</p>
          </div>
        </div>
        <div className={cardClass + " flex items-center gap-3"}>
          <div className="h-9 w-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: "#d977061a" }}>
            <Calendar size={18} style={{ color: "#d97706" }} />
          </div>
          <div>
            <p className={"text-xs " + (isDark ? "text-zinc-500" : "text-gray-400")}>Date</p>
            <p className={"text-sm font-medium capitalize " + (isDark ? "text-white" : "text-gray-800")}>
              {new Date(analyse.date_analyse).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" })}
            </p>
          </div>
        </div>
      </div>

      {/* Résultat + facteurs côte à côte */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ScoreResult result={analyse} onPdf={exporterPdf} />
        <ShapChart result={analyse} />
      </div>
    </div>
  );
}
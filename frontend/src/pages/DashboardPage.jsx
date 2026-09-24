import { useState, useEffect, useRef } from "react";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import Header from "../components/ui/Header";
import MetricCard from "../components/ui/MetricCard";
import { getTableauDeBord } from "../services/dashboardService";
import {
  Users, AlertTriangle, CheckCircle, XCircle, BarChart2, RefreshCw, Loader2,
} from "lucide-react";
import { Chart, registerables } from "chart.js";

Chart.register(...registerables);

// Composant graphiques (histogramme décisions, camembert risques, courbe évolution)
function Graphiques({ data, isDark }) {
  const barRef = useRef(null);
  const camRef = useRef(null);
  const lineRef = useRef(null);
  const charts = useRef({});
  const gridColor = isDark ? "#27272a" : "#f3f4f6";
  const textColor = isDark ? "#71717a" : "#9ca3af";

  useEffect(() => {
    Object.values(charts.current).forEach((c) => c?.destroy());
    charts.current = {};

    // Histogramme des décisions
    if (barRef.current) {
      charts.current.bar = new Chart(barRef.current, {
        type: "bar",
        data: {
          labels: ["Accordés", "Refusés"],
          datasets: [{
            data: [data.decisions.accordes, data.decisions.refuses],
            backgroundColor: [
              isDark ? "rgba(5,150,105,0.7)" : "rgba(15,110,86,0.85)",
              isDark ? "rgba(220,38,38,0.7)" : "rgba(192,57,43,0.85)",
            ],
            borderRadius: 6, borderSkipped: false,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          animation: { duration: 1000, easing: "easeOutQuart" },
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: textColor, font: { size: 10 } }, grid: { display: false } },
            y: { ticks: { color: textColor, font: { size: 10 }, precision: 0 }, grid: { color: gridColor }, beginAtZero: true },
          },
        },
      });
    }

    // Camembert des risques
    if (camRef.current) {
      const r = data.repartition_risque;
      charts.current.cam = new Chart(camRef.current, {
        type: "doughnut",
        data: {
          labels: ["Faible", "Moyen", "Élevé"],
          datasets: [{
            data: [r.faible, r.moyen, r.eleve],
            backgroundColor: ["#0F6E56", "#d97706", "#c0392b"],
            borderWidth: 2, borderColor: isDark ? "#18181b" : "#ffffff",
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          animation: { animateRotate: true, animateScale: true, duration: 1200 },
          cutout: "62%",
          plugins: { legend: { display: false } },
        },
      });
    }

    // Courbe d'évolution
    if (lineRef.current) {
      const evo = data.evolution || [];
      charts.current.line = new Chart(lineRef.current, {
        type: "line",
        data: {
          labels: evo.map((e) => e.jour),
          datasets: [{
            data: evo.map((e) => e.analyses),
            borderColor: "#2E86C1",
            backgroundColor: isDark ? "rgba(46,134,193,0.1)" : "rgba(46,134,193,0.08)",
            borderWidth: 2, pointRadius: 3, pointBackgroundColor: "#2E86C1",
            tension: 0.35, fill: true,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          animation: { duration: 1200, easing: "easeOutQuart" },
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: textColor, font: { size: 10 } }, grid: { display: false } },
            y: { ticks: { color: textColor, font: { size: 10 }, precision: 0 }, grid: { color: gridColor }, beginAtZero: true },
          },
        },
      });
    }

    return () => Object.values(charts.current).forEach((c) => c?.destroy());
  }, [data, isDark]);

  const cardClass = "rounded-2xl border p-4 lg:p-5 transition-colors " +
    (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");
  const labelClass = "font-semibold text-sm " + (isDark ? "text-white" : "text-gray-800");
  const subClass = "text-xs mt-0.5 mb-3 " + (isDark ? "text-zinc-500" : "text-gray-400");
  const legendColor = isDark ? "#71717a" : "#9ca3af";

  const total = data.repartition_risque.faible + data.repartition_risque.moyen + data.repartition_risque.eleve;
  const risques = [
    ["Faible", "#0F6E56", data.repartition_risque.faible],
    ["Moyen", "#d97706", data.repartition_risque.moyen],
    ["Élevé", "#c0392b", data.repartition_risque.eleve],
  ];

  return (
    <div className="mb-5 space-y-4">
      {/* Décisions + Risques côte à côte */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className={cardClass}>
          <p className={labelClass}>Décisions</p>
          <p className={subClass}>Accordés vs refusés</p>
          <div className="flex items-center gap-4 mb-3">
            {[["#0F6E56", "Accordés"], ["#c0392b", "Refusés"]].map((it) => (
              <span key={it[1]} className="flex items-center gap-1.5 text-xs" style={{ color: legendColor }}>
                <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: it[0] }} />
                {it[1]}
              </span>
            ))}
          </div>
          <div style={{ position: "relative", height: "180px" }}><canvas ref={barRef} /></div>
        </div>

        <div className={cardClass}>
          <p className={labelClass}>Répartition par niveau de risque</p>
          <p className={subClass}>Distribution des profils analysés</p>
          <div className="flex flex-wrap gap-x-3 gap-y-1 mb-3">
            {risques.map(([nom, couleur, val]) => (
              <span key={nom} className="flex items-center gap-1.5 text-xs" style={{ color: legendColor }}>
                <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: couleur }} />
                {nom} {total > 0 ? Math.round((val / total) * 100) : 0}%
              </span>
            ))}
          </div>
          <div style={{ position: "relative", height: "180px" }}><canvas ref={camRef} /></div>
        </div>
      </div>

      {/* Évolution pleine largeur */}
      <div className={cardClass}>
        <p className={labelClass}>Évolution des analyses</p>
        <p className={subClass}>Nombre d'analyses sur les 7 derniers jours</p>
        <div style={{ position: "relative", height: "160px" }}><canvas ref={lineRef} /></div>
      </div>
    </div>
  );
}

// Badge de risque
function RiskBadge({ niveau, isDark }) {
  const cfg = {
    faible: isDark ? "text-emerald-400 border-emerald-800" : "text-emerald-700 border-emerald-200",
    moyen: isDark ? "text-amber-400 border-amber-800" : "text-amber-700 border-amber-200",
    eleve: isDark ? "text-red-400 border-red-800" : "text-red-700 border-red-200",
  };
  return (
    <span className={"text-xs px-2 py-0.5 rounded-full border font-medium capitalize whitespace-nowrap " +
      (cfg[niveau] || (isDark ? "text-zinc-400 border-zinc-700" : "text-gray-500 border-gray-200"))}>
      {niveau}
    </span>
  );
}

export default function DashboardPage() {
  const { isDark } = useTheme();
  const { utilisateur } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  async function charger() {
    setLoading(true);
    try { setData(await getTableauDeBord()); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }
  useEffect(() => { charger(); }, []);

  const tableClass = "rounded-2xl border overflow-hidden " +
    (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");
  const headClass = "text-xs uppercase tracking-wider " + (isDark ? "text-zinc-600" : "text-gray-400");
  const cellClass = "py-3 text-xs " + (isDark ? "text-zinc-300" : "text-gray-600");
  const borderB = isDark ? "border-zinc-800" : "border-gray-100";

  const formatRevenu = (r) => (r ? new Intl.NumberFormat("fr-FR").format(r) + " FCFA" : "—");

  return (
    <div>
      <Header title="Tableau de bord" subtitle="Vue d'ensemble du système de scoring crédit" />

      {loading || !data ? (
        <div className="text-center py-16">
          <Loader2 size={28} className={"animate-spin mx-auto mb-3 " + (isDark ? "text-zinc-600" : "text-gray-300")} />
          <p className={"text-sm " + (isDark ? "text-zinc-500" : "text-gray-400")}>Chargement...</p>
        </div>
      ) : (
        <>
          {/* Bandeau statut + actualiser */}
          <div className="flex items-center justify-between mb-5">
            <div className={"flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium border " +
              (isDark ? "border-zinc-800 text-emerald-400" : "border-gray-200 text-emerald-600")}>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              API connectée — {data.modele_production?.algorithme || "modèle"}
              {data.modele_production?.auc && ` (AUC ${data.modele_production.auc})`} opérationnel
            </div>
            <button onClick={charger}
              className={"flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium border transition-all " +
                (isDark ? "border-zinc-800 text-zinc-400 hover:bg-zinc-800" : "border-gray-200 text-gray-500 hover:bg-gray-50")}>
              <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> Actualiser
            </button>
          </div>

          {/* KPI */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4 mb-5">
            <MetricCard title="Dossiers analysés" value={data.totaux.analyses} subtitle="Total historique" icon={Users} color="blue" />
            <MetricCard title="Taux d'accord" value={data.decisions.taux_acceptation} suffix="%" subtitle="Crédits accordés" icon={CheckCircle} color="green" />
            <MetricCard title="Refusés" value={data.decisions.refuses} subtitle="Risque trop élevé" icon={XCircle} color="red" />
            <MetricCard title="Risque moyen" value={data.probabilite_moyenne_defaut} suffix="%" subtitle="Prob. de défaut" icon={AlertTriangle} color="orange" />
          </div>

          {/* Graphiques */}
          <Graphiques data={data} isDark={isDark} />

          {/* Tableau des dernières analyses */}
          <div className={tableClass}>
            <div className={"flex items-center gap-3 p-4 lg:p-5 border-b " + borderB}>
              <BarChart2 size={16} className={isDark ? "text-zinc-500" : "text-gray-400"} />
              <h2 className={"font-semibold text-sm " + (isDark ? "text-white" : "text-gray-800")}>
                Dernières analyses
              </h2>
            </div>
            {data.activite_recente && data.activite_recente.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-140">
                  <thead>
                    <tr className={"border-b " + borderB}>
                      <th className={"text-left py-3 px-4 lg:px-5 " + headClass}>Date</th>
                      <th className={"text-left py-3 " + headClass}>Client</th>
                      <th className={"text-right py-3 " + headClass}>Revenu</th>
                      <th className={"text-center py-3 " + headClass}>Risque</th>
                      <th className={"text-right py-3 " + headClass}>Prob.</th>
                      <th className={"text-center py-3 pr-4 lg:pr-5 " + headClass}>Décision</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.activite_recente.map((a) => (
                      <tr key={a.id} className={"border-t transition-colors " +
                        (isDark ? "border-zinc-800/50 hover:bg-zinc-800/30" : "border-gray-50 hover:bg-gray-50/80")}>
                        <td className={cellClass + " px-4 lg:px-5 whitespace-nowrap"}>{a.date}</td>
                        <td className="py-3">
                          <span className={"text-xs font-medium " + (isDark ? "text-zinc-300" : "text-gray-700")}>{a.nom_client}</span>
                        </td>
                        <td className={cellClass + " text-right whitespace-nowrap"}>{formatRevenu(a.revenu)}</td>
                        <td className="py-3 text-center"><RiskBadge niveau={a.classe_risque} isDark={isDark} /></td>
                        <td className={"py-3 text-right text-xs font-medium " +
                          (a.probabilite_defaut > 50 ? "text-red-500" : "text-emerald-500")}>
                          {a.probabilite_defaut}%
                        </td>
                        <td className="py-3 text-center pr-4 lg:pr-5">
                          <span className={"text-xs px-2 py-0.5 rounded-full font-medium border " +
                            (a.decision === "ACCORDE"
                              ? (isDark ? "text-emerald-400 border-emerald-800" : "text-emerald-700 border-emerald-200")
                              : (isDark ? "text-red-400 border-red-800" : "text-red-700 border-red-200"))}>
                            {a.decision === "ACCORDE" ? "Accordé" : "Refusé"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className={"text-center py-10 text-sm " + (isDark ? "text-zinc-500" : "text-gray-400")}>
                Aucune analyse pour l'instant.
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
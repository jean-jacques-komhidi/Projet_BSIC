import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import Header from "../components/ui/Header";
import MetricCard from "../components/ui/MetricCard";
import { getTableauDeBord } from "../services/dashboardService";
import { telechargerPdf } from "../services/analyseService";
import {
  Users, AlertTriangle, CheckCircle, ClipboardCheck, RefreshCw, Loader2, Download, ChevronRight,
} from "lucide-react";
import { Chart, registerables } from "chart.js";

Chart.register(...registerables);

// Couleurs de l'application : chaque couleur garde un seul sens
const BLEU = "#2E86C1";      // application, neutre
const VERT = "#0F6E56";      // accordé, risque faible
const ORANGE = "#d97706";    // risque moyen, à surveiller
const ROUGE = "#c0392b";     // refusé, risque élevé

// Seuils du modèle (identiques au backend)
const SEUIL_RISQUE_FAIBLE = 40;
const SEUIL_REFUS = 70;

const PERIODES = [
  { cle: "7j", libelle: "7 jours", texte: "Sur les 7 derniers jours" },
  { cle: "30j", libelle: "30 jours", texte: "Sur les 30 derniers jours" },
  { cle: "tout", libelle: "Tout", texte: "Depuis le début" },
];

// Nombres au format français : 79,4 — 2 500 000
const nombre = (n, decimales = 1) =>
  n === null || n === undefined ? "—" : Number(n).toLocaleString("fr-FR", { maximumFractionDigits: decimales });
const fcfa = (n) => (n ? nombre(n, 0) + " FCFA" : "—");

function niveauDeProbabilite(p) {
  if (p < SEUIL_RISQUE_FAIBLE) return "faible";
  if (p < SEUIL_REFUS) return "moyen";
  return "eleve";
}

// Valeurs affichées au-dessus des barres (lisibles sans se fier à la couleur)
const valeursSurBarres = (couleurTexte) => ({
  id: "valeursSurBarres",
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    ctx.save();
    ctx.font = "600 10px Inter, system-ui, sans-serif";
    ctx.fillStyle = couleurTexte;
    ctx.textAlign = "center";
    chart.data.datasets.forEach((ds, i) => {
      chart.getDatasetMeta(i).data.forEach((barre, j) => {
        if (ds.data[j] > 0) ctx.fillText(ds.data[j], barre.x, barre.y - 5);
      });
    });
    ctx.restore();
  },
});

// Légende des graphiques : pastille de couleur + texte
function Legende({ items, couleurTexte }) {
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 mb-3">
      {items.map(([texte, couleur]) => (
        <span key={texte} className="flex items-center gap-1.5 text-xs" style={{ color: couleurTexte }}>
          <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: couleur }} />
          {texte}
        </span>
      ))}
    </div>
  );
}

// Graphiques : décisions par montant, répartition des risques, évolution
function Graphiques({ data, isDark, periode }) {
  const barRef = useRef(null);
  const camRef = useRef(null);
  const lineRef = useRef(null);
  const charts = useRef({});
  const gridColor = isDark ? "#27272a" : "#f3f4f6";
  const textColor = isDark ? "#71717a" : "#9ca3af";
  const ligneColor = isDark ? "#cbd5e1" : "#0B2A4F";

  useEffect(() => {
    Object.values(charts.current).forEach((c) => c?.destroy());
    charts.current = {};
    const axeX = { ticks: { color: textColor, font: { size: 10 } }, grid: { display: false } };
    const axeY = { ticks: { color: textColor, font: { size: 10 }, precision: 0 }, grid: { color: gridColor }, beginAtZero: true };

    // Décisions selon le montant demandé
    if (barRef.current) {
      const tranches = data.decisions_par_montant || [];
      charts.current.bar = new Chart(barRef.current, {
        type: "bar",
        data: {
          labels: tranches.map((t) => t.tranche),
          datasets: [
            { label: "Accordés", data: tranches.map((t) => t.accordes),
              backgroundColor: isDark ? "rgba(5,150,105,0.75)" : "rgba(15,110,86,0.85)", borderRadius: 5, borderSkipped: false },
            { label: "Refusés", data: tranches.map((t) => t.refuses),
              backgroundColor: isDark ? "rgba(220,38,38,0.7)" : "rgba(192,57,43,0.85)", borderRadius: 5, borderSkipped: false },
          ],
        },
        plugins: [valeursSurBarres(isDark ? "#d4d4d8" : "#4b5563")],
        options: {
          responsive: true, maintainAspectRatio: false,
          animation: { duration: 800, easing: "easeOutQuart" },
          layout: { padding: { top: 14 } },
          datasets: { bar: { categoryPercentage: 0.7, barPercentage: 0.85 } },
          plugins: { legend: { display: false } },
          scales: {
            x: { ...axeX, title: { display: true, text: "Montant demandé (FCFA)", color: textColor, font: { size: 10 } } },
            y: axeY,
          },
        },
      });
    }

    // Répartition des risques
    if (camRef.current) {
      const r = data.repartition_risque;
      charts.current.cam = new Chart(camRef.current, {
        type: "doughnut",
        data: {
          labels: ["Faible", "Moyen", "Élevé"],
          datasets: [{
            data: [r.faible, r.moyen, r.eleve],
            backgroundColor: [VERT, ORANGE, ROUGE],
            borderWidth: 2, borderColor: isDark ? "#18181b" : "#ffffff",
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          animation: { animateRotate: true, duration: 900 },
          cutout: "62%",
          plugins: { legend: { display: false } },
        },
      });
    }

    // Évolution : analyses (barres) et probabilité moyenne de défaut (courbe)
    if (lineRef.current) {
      const evo = data.evolution || [];
      charts.current.line = new Chart(lineRef.current, {
        data: {
          labels: evo.map((e) => e.jour),
          datasets: [
            { type: "bar", label: "Analyses", data: evo.map((e) => e.analyses), yAxisID: "y",
              backgroundColor: isDark ? "rgba(46,134,193,0.6)" : "rgba(46,134,193,0.75)", borderRadius: 4 },
            { type: "line", label: "Probabilité moyenne de défaut", data: evo.map((e) => e.risque_moyen), yAxisID: "y2",
              borderColor: ligneColor, backgroundColor: ligneColor, borderWidth: 2, pointRadius: 2,
              tension: 0.35, spanGaps: true },
          ],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          animation: { duration: 800, easing: "easeOutQuart" },
          plugins: { legend: { display: false } },
          scales: {
            x: { ...axeX, ticks: { ...axeX.ticks, maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } },
            y: axeY,
            y2: { position: "right", min: 0, max: 100, grid: { display: false },
              ticks: { color: textColor, font: { size: 10 }, callback: (v) => v + " %" } },
          },
        },
      });
    }

    return () => Object.values(charts.current).forEach((c) => c?.destroy());
  }, [data, isDark, gridColor, textColor, ligneColor]);

  const cardClass = "rounded-2xl border p-4 lg:p-5 transition-colors " +
    (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");
  const labelClass = "font-semibold text-sm " + (isDark ? "text-white" : "text-gray-800");
  const subClass = "text-xs mt-0.5 mb-3 " + (isDark ? "text-zinc-500" : "text-gray-400");
  const legendColor = isDark ? "#a1a1aa" : "#6b7280";

  const r = data.repartition_risque;
  const total = r.faible + r.moyen + r.eleve;
  const pct = (v) => (total > 0 ? Math.round((v / total) * 100) : 0);
  const sousTitreEvolution = periode === "tout"
    ? "Analyses par mois et probabilité moyenne de défaut, sur 12 mois"
    : `Analyses par jour et probabilité moyenne de défaut, sur ${periode === "7j" ? "7" : "30"} jours`;

  return (
    <div className="mb-5 space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className={cardClass}>
          <p className={labelClass}>Décisions</p>
          <p className={subClass}>Accordés et refusés selon le montant demandé</p>
          <Legende couleurTexte={legendColor} items={[[`Accordés ${data.decisions.accordes}`, VERT], [`Refusés ${data.decisions.refuses}`, ROUGE]]} />
          <div style={{ position: "relative", height: "200px" }}><canvas ref={barRef} /></div>
        </div>

        <div className={cardClass}>
          <p className={labelClass}>Répartition par niveau de risque</p>
          <p className={subClass}>Distribution des profils analysés</p>
          <Legende couleurTexte={legendColor} items={[
            [`Faible ${r.faible} (${pct(r.faible)} %)`, VERT],
            [`Moyen ${r.moyen} (${pct(r.moyen)} %)`, ORANGE],
            [`Élevé ${r.eleve} (${pct(r.eleve)} %)`, ROUGE],
          ]} />
          <div style={{ position: "relative", height: "200px" }}><canvas ref={camRef} /></div>
        </div>
      </div>

      <div className={cardClass}>
        <p className={labelClass}>Évolution des analyses</p>
        <p className={subClass}>{sousTitreEvolution}</p>
        <Legende couleurTexte={legendColor} items={[["Analyses", BLEU], ["Probabilité moyenne de défaut", ligneColor]]} />
        <div style={{ position: "relative", height: "190px" }}><canvas ref={lineRef} /></div>
      </div>
    </div>
  );
}

// Pastille (niveau de risque ou décision)
function Pastille({ ton, children, isDark }) {
  const cfg = {
    faible: isDark ? "text-emerald-400 border-emerald-800" : "text-emerald-700 border-emerald-200",
    moyen: isDark ? "text-amber-400 border-amber-800" : "text-amber-700 border-amber-200",
    eleve: isDark ? "text-red-400 border-red-800" : "text-red-700 border-red-200",
  };
  return (
    <span className={"text-xs px-2 py-0.5 rounded-full border font-medium whitespace-nowrap " +
      (cfg[ton] || (isDark ? "text-zinc-400 border-zinc-700" : "text-gray-500 border-gray-200"))}>
      {children}
    </span>
  );
}

const LIBELLE_RISQUE = { faible: "Faible", moyen: "Moyen", eleve: "Élevé" };
const COULEUR_PROBA = {
  faible: { clair: "text-emerald-700", sombre: "text-emerald-400" },
  moyen: { clair: "text-amber-700", sombre: "text-amber-400" },
  eleve: { clair: "text-red-700", sombre: "text-red-400" },
};

export default function DashboardPage() {
  const { isDark } = useTheme();
  const { utilisateur } = useAuth();
  const navigate = useNavigate();
  const estAdmin = utilisateur?.role === "admin";
  const [periode, setPeriode] = useState("30j");
  const [version, setVersion] = useState(0);
  const [data, setData] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");
  const [pdfEnCours, setPdfEnCours] = useState(null);

  useEffect(() => {
    let actif = true;
    getTableauDeBord(periode)
      .then((d) => { if (actif) { setData(d); setErreur(""); } })
      .catch(() => { if (actif) setErreur("Impossible de charger le tableau de bord. Vérifiez la connexion, puis actualisez."); })
      .finally(() => { if (actif) setChargement(false); });
    return () => { actif = false; };
  }, [periode, version]);

  function changerPeriode(cle) {
    if (cle === periode) return;
    setChargement(true);
    setPeriode(cle);
  }
  function actualiser() {
    setChargement(true);
    setVersion((v) => v + 1);
  }

  async function telecharger(e, id) {
    e.stopPropagation();
    setPdfEnCours(id);
    try {
      const blob = await telechargerPdf(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `fiche_decision_${id}.pdf`; a.click();
      URL.revokeObjectURL(url);
    } catch {
      setErreur("Le téléchargement de la fiche PDF a échoué. Réessayez.");
    } finally {
      setPdfEnCours(null);
    }
  }

  const carteClass = "rounded-2xl border overflow-hidden " +
    (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");
  const titreCarte = "font-semibold text-sm " + (isDark ? "text-white" : "text-gray-800");
  const sousTitre = "text-xs mt-0.5 " + (isDark ? "text-zinc-500" : "text-gray-400");
  const headClass = "text-left py-2.5 text-[11px] font-medium " + (isDark ? "text-zinc-500" : "text-gray-400");
  const cellClass = "py-3 text-xs " + (isDark ? "text-zinc-300" : "text-gray-600");
  const ligneClass = "border-t cursor-pointer transition-colors " +
    (isDark ? "border-zinc-800/60 hover:bg-zinc-800/40" : "border-gray-50 hover:bg-gray-50");
  const bordure = isDark ? "border-zinc-800" : "border-gray-100";
  const boutonClass = "flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium border transition " +
    (isDark ? "border-zinc-800 text-zinc-400 hover:bg-zinc-800 bg-zinc-900" : "border-gray-200 text-gray-500 hover:bg-gray-50 bg-white");

  const periodeActive = PERIODES.find((p) => p.cle === periode);
  const auc = data?.modele_production?.auc;
  const issues = data?.issues_reelles || { renseignees: 0, credits_accordes: 0 };
  const pctSuivis = issues.credits_accordes ? Math.round((100 * issues.renseignees) / issues.credits_accordes) : 0;
  const suivre = data?.dossiers_a_suivre || { total: 0, liste: [], delai_jours: 30 };

  return (
    <div>
      <Header title="Tableau de bord" subtitle="Vue d'ensemble du système de scoring crédit" />

      {!data && chargement ? (
        <div className="text-center py-16">
          <Loader2 size={28} className={"animate-spin mx-auto mb-3 " + (isDark ? "text-zinc-600" : "text-gray-300")} />
          <p className={"text-sm " + (isDark ? "text-zinc-500" : "text-gray-400")}>Chargement…</p>
        </div>
      ) : !data ? (
        <div className={"rounded-xl border px-4 py-3 text-sm " +
          (isDark ? "bg-red-500/10 border-red-900 text-red-400" : "bg-red-50 border-red-200 text-red-700")}>
          {erreur}
          <button onClick={actualiser} className="ml-3 underline font-medium">Actualiser</button>
        </div>
      ) : (
        <>
          {/* Statut, période, actualiser */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
            <div className={"flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium border " +
              (isDark ? "border-zinc-800 text-emerald-400 bg-zinc-900" : "border-gray-200 text-emerald-600 bg-white")}>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              API connectée — {data.modele_production?.algorithme || "modèle"}
              {auc ? ` (AUC ${nombre(auc, 3)})` : ""} opérationnel
            </div>
            <div className="flex items-center gap-2">
              <div role="group" aria-label="Période"
                className={"flex p-0.5 rounded-xl border " + (isDark ? "border-zinc-800 bg-zinc-900" : "border-gray-200 bg-white")}>
                {PERIODES.map((p) => (
                  <button key={p.cle} onClick={() => changerPeriode(p.cle)} aria-pressed={periode === p.cle}
                    className={"px-3 py-1.5 rounded-lg text-xs font-medium transition " +
                      (periode === p.cle ? "text-white" : (isDark ? "text-zinc-400 hover:text-zinc-200" : "text-gray-500 hover:text-gray-700"))}
                    style={periode === p.cle ? { backgroundColor: BLEU } : undefined}>
                    {p.libelle}
                  </button>
                ))}
              </div>
              <button onClick={actualiser} className={boutonClass}>
                <RefreshCw size={13} className={chargement ? "animate-spin" : ""} /> Actualiser
              </button>
            </div>
          </div>

          {erreur && (
            <div role="alert" className={"rounded-xl border px-4 py-2.5 text-xs mb-4 " +
              (isDark ? "bg-red-500/10 border-red-900 text-red-400" : "bg-red-50 border-red-200 text-red-700")}>{erreur}</div>
          )}

          {/* Indicateurs */}
          <div className={"grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4 mb-5 transition-opacity " + (chargement ? "opacity-60" : "")}>
            <MetricCard title="Dossiers analysés" value={nombre(data.totaux.analyses, 0)}
              subtitle={periodeActive.texte} icon={Users} color="blue" />
            <MetricCard title="Taux d'accord" value={nombre(data.decisions.taux_acceptation)} suffix=" %"
              subtitle={`${data.decisions.accordes} accordés · ${data.decisions.refuses} refusés`} icon={CheckCircle} color="green" />
            <MetricCard title="Probabilité moyenne de défaut" value={nombre(data.probabilite_moyenne_defaut)} suffix=" %"
              subtitle={`Seuil de refus : ${SEUIL_REFUS} %`} icon={AlertTriangle} color="orange" />
            <MetricCard title="Issues réelles renseignées" value={`${issues.renseignees} / ${issues.credits_accordes}`}
              subtitle={`${pctSuivis} % des crédits accordés suivis`} icon={ClipboardCheck} color="blue" />
          </div>

          <div className={"transition-opacity " + (chargement ? "opacity-60" : "")}>
            <Graphiques data={data} isDark={isDark} periode={periode} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Dossiers à suivre */}
            <div className={carteClass}>
              <div className={"p-4 lg:p-5 border-b " + bordure}>
                <div className="flex items-center gap-2">
                  <h2 className={titreCarte}>Dossiers à suivre</h2>
                  {suivre.total > 0 && (
                    <span className={"text-[11px] font-semibold px-2 py-0.5 rounded-full " +
                      (isDark ? "bg-amber-500/15 text-amber-400" : "bg-amber-100 text-amber-700")}>{suivre.total}</span>
                  )}
                </div>
                <p className={sousTitre}>
                  Crédits accordés il y a plus de {suivre.delai_jours} jours, sans issue renseignée
                  {estAdmin ? "" : " (vos dossiers)"}
                </p>
              </div>
              {suivre.liste.length > 0 ? (
                <div className="overflow-x-auto px-4 lg:px-5">
                  <table className="w-full min-w-[420px]">
                    <thead><tr>
                      <th className={headClass}>Client</th><th className={headClass}>Accordé le</th>
                      <th className={headClass}>Montant</th><th className={headClass}></th>
                    </tr></thead>
                    <tbody>
                      {suivre.liste.map((d) => (
                        <tr key={d.id} className={ligneClass} onClick={() => navigate(`/analyse/${d.id}`)}>
                          <td className={cellClass + " font-medium " + (isDark ? "text-zinc-200" : "text-gray-800")}>{d.nom_client}</td>
                          <td className={"py-3 text-xs whitespace-nowrap " + (d.jours > 60
                            ? (isDark ? "text-amber-400 font-medium" : "text-amber-700 font-medium")
                            : (isDark ? "text-zinc-300" : "text-gray-600"))}
                            title={`Il y a ${d.jours} jours`}>{d.date}</td>
                          <td className={cellClass + " whitespace-nowrap"}>{fcfa(d.montant)}</td>
                          <td className="py-3 text-right">
                            <span className="inline-flex items-center gap-0.5 text-xs font-medium whitespace-nowrap" style={{ color: BLEU }}>
                              {estAdmin ? "Renseigner l'issue" : "Voir le dossier"} <ChevronRight size={14} />
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className={"text-center py-10 text-sm " + (isDark ? "text-zinc-500" : "text-gray-400")}>
                  Aucun dossier en attente : toutes les issues sont à jour.
                </p>
              )}
            </div>

            {/* Dernières analyses */}
            <div className={carteClass}>
              <div className={"p-4 lg:p-5 border-b " + bordure}>
                <h2 className={titreCarte}>Dernières analyses</h2>
                <p className={sousTitre}>Cliquez sur une ligne pour ouvrir le détail</p>
              </div>
              {data.activite_recente?.length > 0 ? (
                <div className="overflow-x-auto px-4 lg:px-5">
                  <table className="w-full min-w-[480px]">
                    <thead><tr>
                      <th className={headClass}>Date</th><th className={headClass}>Client</th>
                      <th className={headClass}>Risque</th><th className={headClass + " text-right"}>Prob.</th>
                      <th className={headClass + " pl-3"}>Décision</th><th className={headClass}></th>
                    </tr></thead>
                    <tbody>
                      {data.activite_recente.map((a) => {
                        const niveau = a.classe_risque || niveauDeProbabilite(a.probabilite_defaut);
                        const couleur = COULEUR_PROBA[niveau] || COULEUR_PROBA.faible;
                        return (
                          <tr key={a.id} className={ligneClass} onClick={() => navigate(`/analyse/${a.id}`)}>
                            <td className={cellClass + " whitespace-nowrap"}>{a.date}</td>
                            <td className={cellClass + " font-medium " + (isDark ? "text-zinc-200" : "text-gray-800")}>{a.nom_client}</td>
                            <td className="py-3"><Pastille ton={niveau} isDark={isDark}>{LIBELLE_RISQUE[niveau] || niveau}</Pastille></td>
                            <td className={"py-3 text-right text-xs font-semibold " + (isDark ? couleur.sombre : couleur.clair)}>
                              {nombre(a.probabilite_defaut)} %
                            </td>
                            <td className="py-3 pl-3">
                              <Pastille ton={a.decision === "ACCORDE" ? "faible" : "eleve"} isDark={isDark}>
                                {a.decision === "ACCORDE" ? "Accordé" : "Refusé"}
                              </Pastille>
                            </td>
                            <td className="py-3 text-right">
                              <button onClick={(e) => telecharger(e, a.id)} aria-label="Télécharger la fiche PDF"
                                title="Télécharger la fiche PDF"
                                className={"inline-flex w-7 h-7 items-center justify-center rounded-lg border transition " +
                                  (isDark ? "border-zinc-700 text-zinc-400 hover:bg-zinc-800" : "border-gray-200 text-gray-500 hover:bg-gray-50")}>
                                {pdfEnCours === a.id ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className={"text-center py-10 text-sm " + (isDark ? "text-zinc-500" : "text-gray-400")}>
                  Aucune analyse pour l'instant. Lancez une première analyse depuis « Analyse de crédit ».
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

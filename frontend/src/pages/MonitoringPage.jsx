import { useState, useEffect, useRef } from "react";
import { useTheme } from "../context/ThemeContext";
import Header from "../components/ui/Header";
import {
  getMlflowRuns, lancerRetrain, getRetrainStatus, getDrift,
} from "../services/monitoringService";
import {
  Activity, RefreshCw, Loader2, CheckCircle2, AlertTriangle, XCircle,
  Database, Award, Zap, TrendingUp, TrendingDown,
} from "lucide-react";

const fmt = (n) => n?.toLocaleString("fr-FR") ?? "—";

const uniteVariable = (variable) => {
  if (variable === "AGE_ANNEES" || variable === "ANCIENNETE_EMPLOI_ANNEES") return "ans";
  return "FCFA";
};

export default function MonitoringPage() {
  const { isDark } = useTheme();
  const [runs, setRuns] = useState([]);
  const [drift, setDrift] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState(false);
  const pollRef = useRef(null);

  // Chargement progressif : chaque donnée se charge indépendamment
  function chargerTout() {
    setLoading(true);
    getRetrainStatus().then(setStatus).catch(() => {});
    getMlflowRuns().then(setRuns).catch(() => setRuns([]));
    getDrift().then(setDrift).catch(() => setDrift(null)).finally(() => setLoading(false));
  }
  useEffect(() => { chargerTout(); }, []);
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  function demarrerPolling() {
    pollRef.current = setInterval(async () => {
      try {
        const s = await getRetrainStatus();
        setStatus(s);
        if (!s.running) {
          clearInterval(pollRef.current);
          getMlflowRuns().then(setRuns).catch(() => {});
          getDrift().then(setDrift).catch(() => {});
        }
      } catch {}
    }, 2000);
  }
  async function reentrainer() {
    setLaunching(true);
    try { await lancerRetrain(); demarrerPolling(); }
    catch {} finally { setLaunching(false); }
  }

  const cardClass = "rounded-2xl border " + (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");
  const borderB = isDark ? "border-zinc-800" : "border-gray-100";
  const headClass = "text-xs font-medium uppercase tracking-wider " + (isDark ? "text-zinc-600" : "text-gray-400");

  const bestRun = runs[0];
  const isRunning = status?.running;
  const lastResult = status?.last_result;
  const version = status?.current_version || "1.0";

  const driftOk = drift?.statut === "ok";
  const features = drift?.drift_features || [];
  const hasCritical = features.some((f) => f.statut === "CRITIQUE");
  const hasAlert = features.some((f) => f.statut === "ALERTE");

  function cfgStatut(statut) {
    if (statut === "CRITIQUE") return { Icone: XCircle, couleur: "#c0392b", barre: "#c0392b",
      classe: isDark ? "text-red-400 border-red-900" : "text-red-600 border-red-200" };
    if (statut === "ALERTE") return { Icone: AlertTriangle, couleur: "#d97706", barre: "#d97706",
      classe: isDark ? "text-amber-400 border-amber-900" : "text-amber-600 border-amber-200" };
    return { Icone: CheckCircle2, couleur: "#0F6E56", barre: "#0F6E56",
      classe: isDark ? "text-emerald-400 border-emerald-900" : "text-emerald-600 border-emerald-200" };
  }

  return (
    <div>
      <Header title="Monitoring" subtitle="Suivi MLflow et détection de la dérive" />

      {/* Barre supérieure */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <Activity size={15} className={isDark ? "text-zinc-500" : "text-gray-400"} />
          <span className={"font-semibold text-sm " + (isDark ? "text-white" : "text-gray-800")}>Tableau de monitoring</span>
          <span className={"text-xs px-2 py-0.5 rounded-full border font-medium " + (isDark ? "border-zinc-700 text-zinc-500" : "border-gray-200 text-gray-400")}>
            v{version}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={chargerTout}
            className={"flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border transition " +
              (isDark ? "border-zinc-800 text-zinc-400 hover:bg-zinc-800" : "border-gray-200 text-gray-500 hover:bg-gray-50")}>
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
            <span className="hidden sm:inline">Actualiser</span>
          </button>
          <button onClick={reentrainer} disabled={isRunning || launching}
            className={"flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition text-white " +
              (isRunning || launching ? "opacity-60 cursor-not-allowed" : "hover:opacity-90")}
            style={{ backgroundColor: hasCritical ? "#c0392b" : "#2E86C1" }}>
            {isRunning || launching ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
            <span>{isRunning ? "Réentraînement..." : launching ? "Lancement..." : "Réentraîner le modèle"}</span>
          </button>
        </div>
      </div>

      {/* Bandeau drift */}
      {driftOk && (
        <div className={"flex items-center gap-3 px-4 py-3 rounded-xl border mb-5 " +
          (hasCritical ? (isDark ? "border-red-900 bg-red-500/5" : "border-red-200 bg-red-50/50")
            : hasAlert ? (isDark ? "border-amber-900 bg-amber-500/5" : "border-amber-200 bg-amber-50/50")
            : (isDark ? "border-emerald-900 bg-emerald-500/5" : "border-emerald-200 bg-emerald-50/50"))}>
          <span className={"w-2 h-2 rounded-full " + (hasCritical ? "bg-red-500" : hasAlert ? "bg-amber-500" : "bg-emerald-500")} />
          <span className={"text-xs font-medium " +
            (hasCritical ? (isDark ? "text-red-400" : "text-red-700") : hasAlert ? (isDark ? "text-amber-400" : "text-amber-700") : (isDark ? "text-emerald-400" : "text-emerald-700"))}>
            Data Drift — {drift.recommandation}
          </span>
          <span className={"text-xs ml-auto " + (isDark ? "text-zinc-500" : "text-gray-400")}>{drift.total_predictions} prédictions analysées</span>
        </div>
      )}

      {/* Barre de progression */}
      {isRunning && (
        <div className={cardClass + " p-4 mb-5"}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Loader2 size={13} className="animate-spin" style={{ color: "#2E86C1" }} />
              <span className={"text-xs font-medium " + (isDark ? "text-white" : "text-gray-800")}>Réentraînement en cours</span>
            </div>
            <span className="text-xs font-semibold" style={{ color: "#2E86C1" }}>{status?.progress || 0}%</span>
          </div>
          <div className={"w-full h-1.5 rounded-full mb-2 " + (isDark ? "bg-zinc-800" : "bg-gray-100")}>
            <div className="h-1.5 rounded-full transition-all duration-500" style={{ width: (status?.progress || 0) + "%", backgroundColor: "#2E86C1" }} />
          </div>
          <p className={"text-xs " + (isDark ? "text-zinc-500" : "text-gray-400")}>{status?.message}</p>
        </div>
      )}

      {/* Résultat dernier réentraînement */}
      {!isRunning && lastResult && (
        <div className={"rounded-2xl border p-4 mb-5 " +
          (lastResult.improved ? (isDark ? "bg-emerald-500/5 border-emerald-900" : "bg-emerald-50 border-emerald-200")
            : (isDark ? "bg-amber-500/5 border-amber-900" : "bg-amber-50 border-amber-200"))}>
          <div className="flex items-center gap-2 mb-3">
            {lastResult.improved
              ? <CheckCircle2 size={14} className={isDark ? "text-emerald-400" : "text-emerald-600"} />
              : <AlertTriangle size={14} className={isDark ? "text-amber-400" : "text-amber-600"} />}
            <span className={"text-xs font-semibold " +
              (lastResult.improved ? (isDark ? "text-emerald-400" : "text-emerald-700") : (isDark ? "text-amber-400" : "text-amber-700"))}>
              {lastResult.improved ? `${lastResult.best_model} déployé avec succès !` : "Réentraînement terminé"}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className={"rounded-lg p-2.5 " + (isDark ? "bg-zinc-800/50" : "bg-white/70")}>
              <p className={"text-xs mb-0.5 " + (isDark ? "text-zinc-500" : "text-gray-400")}>AUC avant</p>
              <p className={"text-sm font-bold " + (isDark ? "text-zinc-300" : "text-gray-600")}>{lastResult.old_auc || "—"}</p>
            </div>
            <div className={"rounded-lg p-2.5 " + (isDark ? "bg-zinc-800/50" : "bg-white/70")}>
              <p className={"text-xs mb-0.5 " + (isDark ? "text-zinc-500" : "text-gray-400")}>AUC après</p>
              <p className={"text-sm font-bold flex items-center gap-1 " +
                (lastResult.improved ? (isDark ? "text-emerald-400" : "text-emerald-600") : (isDark ? "text-amber-400" : "text-amber-600"))}>
                {lastResult.new_auc} {lastResult.improved ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
              </p>
            </div>
            <div className={"rounded-lg p-2.5 " + (isDark ? "bg-zinc-800/50" : "bg-white/70")}>
              <p className={"text-xs mb-0.5 " + (isDark ? "text-zinc-500" : "text-gray-400")}>Données réelles</p>
              <p className={"text-sm font-bold " + (isDark ? "text-zinc-300" : "text-gray-600")}>{lastResult.donnees_reelles}</p>
            </div>
          </div>
          <p className={"text-xs mt-3 " + (isDark ? "text-zinc-600" : "text-gray-400")}>{lastResult.timestamp}</p>
        </div>
      )}

      {/* 4 KPI */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        <div className={cardClass + " p-4"}>
          <p className={"text-xs mb-1 " + (isDark ? "text-zinc-500" : "text-gray-400")}>Meilleur AUC-ROC</p>
          <p className={"text-xl font-bold " + (isDark ? "text-white" : "text-gray-800")}>{bestRun?.auc_roc || "—"}</p>
          <p className={"text-xs mt-0.5 " + (isDark ? "text-zinc-600" : "text-gray-400")}>{bestRun?.modele || "—"}</p>
        </div>
        <div className={cardClass + " p-4"}>
          <p className={"text-xs mb-1 " + (isDark ? "text-zinc-500" : "text-gray-400")}>Coût métier</p>
          <p className={"text-xl font-bold " + (isDark ? "text-white" : "text-gray-800")}>{fmt(bestRun?.score_metier)}</p>
          <p className={"text-xs mt-0.5 " + (isDark ? "text-zinc-600" : "text-gray-400")}>Meilleur run</p>
        </div>
        <div className={cardClass + " p-4"}>
          <p className={"text-xs mb-1 " + (isDark ? "text-zinc-500" : "text-gray-400")}>Expériences</p>
          <p className={"text-xl font-bold " + (isDark ? "text-white" : "text-gray-800")}>{runs.length}</p>
          <p className={"text-xs mt-0.5 " + (isDark ? "text-zinc-600" : "text-gray-400")}>Runs MLflow</p>
        </div>
        <div className={cardClass + " p-4"}>
          <p className={"text-xs mb-1 " + (isDark ? "text-zinc-500" : "text-gray-400")}>Statut dérive</p>
          <p className={"text-xl font-bold " +
            (hasCritical ? (isDark ? "text-red-400" : "text-red-600") : hasAlert ? (isDark ? "text-amber-400" : "text-amber-600") : (isDark ? "text-emerald-400" : "text-emerald-600"))}>
            {hasCritical ? "CRITIQUE" : hasAlert ? "ALERTE" : driftOk ? "NORMAL" : "—"}
          </p>
          <p className={"text-xs mt-0.5 " + (isDark ? "text-zinc-600" : "text-gray-400")}>{features.length} variables</p>
        </div>
      </div>

      {/* Grille MLflow + Drift détaillé */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* MLflow */}
        <div>
          <p className={"mb-3 " + headClass}>Expériences MLflow</p>
          <div className={cardClass}>
            {runs.length === 0 ? (
              <div className="text-center py-12">
                <Activity size={26} className={"mx-auto mb-3 " + (isDark ? "text-zinc-700" : "text-gray-300")} />
                <p className={"text-sm " + (isDark ? "text-zinc-500" : "text-gray-400")}>Aucun run MLflow</p>
                <p className={"text-xs mt-1 " + (isDark ? "text-zinc-600" : "text-gray-400")}>Lancez le serveur MLflow (port 5000)</p>
              </div>
            ) : (
              <div>
                {bestRun && (
                  <div className={"p-4 border-b " + borderB}>
                    <div className="flex items-center gap-2 mb-2">
                      <Award size={13} className={isDark ? "text-amber-400" : "text-amber-500"} />
                      <p className={"text-xs font-medium " + (isDark ? "text-zinc-400" : "text-gray-500")}>Meilleur modèle en production</p>
                    </div>
                    <div className="flex items-start justify-between">
                      <div>
                        <p className={"font-semibold text-sm " + (isDark ? "text-white" : "text-gray-800")}>{bestRun.modele}</p>
                        <p className={"text-xs mt-0.5 " + (isDark ? "text-zinc-500" : "text-gray-400")}>ID : {bestRun.run_id} · terminé</p>
                      </div>
                      <div className="text-right">
                        <p className={"text-lg font-bold " + (isDark ? "text-white" : "text-gray-800")}>{bestRun.auc_roc}</p>
                        <p className={"text-xs " + (isDark ? "text-zinc-500" : "text-gray-400")}>AUC-ROC</p>
                      </div>
                    </div>
                  </div>
                )}
                <div className="overflow-x-auto">
                  <table className="w-full min-w-85">
                    <thead>
                      <tr className={"border-b " + borderB}>
                        <th className={"text-left py-2.5 px-4 " + headClass}>Modèle</th>
                        <th className={"text-center py-2.5 " + headClass}>AUC</th>
                        <th className={"text-center py-2.5 pr-4 " + headClass}>Coût</th>
                      </tr>
                    </thead>
                    <tbody>
                      {runs.map((run, i) => (
                        <tr key={run.run_id + i} className={"border-t " + (isDark ? "border-zinc-800/50" : "border-gray-50")}>
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              <span className={"text-xs font-medium " + (isDark ? "text-zinc-200" : "text-gray-700")}>{run.modele}</span>
                              {i === 0 && <span className={"text-xs px-1.5 py-0.5 rounded border font-medium " + (isDark ? "border-amber-900 text-amber-400" : "border-amber-200 text-amber-600")}>Best</span>}
                            </div>
                          </td>
                          <td className={"py-3 text-center text-xs font-semibold " + (i === 0 ? (isDark ? "text-emerald-400" : "text-emerald-600") : (isDark ? "text-zinc-300" : "text-gray-600"))}>{run.auc_roc}</td>
                          <td className={"py-3 text-center text-xs pr-4 " + (isDark ? "text-zinc-400" : "text-gray-500")}>{fmt(run.score_metier)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Drift détaillé */}
        <div>
          <p className={"mb-3 " + headClass}>Analyse du Data Drift</p>
          <div className={cardClass}>
            {loading && !drift ? (
              <div className="text-center py-12"><Loader2 size={24} className={"animate-spin mx-auto " + (isDark ? "text-zinc-600" : "text-gray-300")} /></div>
            ) : !driftOk ? (
              <div className="text-center py-12">
                <Database size={26} className={"mx-auto mb-3 " + (isDark ? "text-zinc-700" : "text-gray-300")} />
                <p className={"text-sm " + (isDark ? "text-zinc-500" : "text-gray-400")}>{drift?.message || "Données insuffisantes"}</p>
              </div>
            ) : (
              <div>
                {features.map((f, i) => {
                  const { Icone, couleur, barre, classe } = cfgStatut(f.statut);
                  const isLast = i === features.length - 1;
                  const niveauTexte = f.z_score <= 1 ? "Distribution normale" : f.z_score <= 2 ? "Dérive modérée" : "Dérive significative";
                  const unite = uniteVariable(f.variable);
                  return (
                    <div key={f.variable} className={"p-4 " + (!isLast ? "border-b " + borderB : "")}>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <div className={"w-7 h-7 rounded-lg border flex items-center justify-center " + classe}>
                            <Icone size={13} />
                          </div>
                          <p className={"text-sm font-medium " + (isDark ? "text-white" : "text-gray-800")}>{f.feature}</p>
                        </div>
                        <span className={"text-xs px-2 py-0.5 rounded-full border font-medium " + classe}>{f.statut}</span>
                      </div>
                      <div className="mb-3">
                        <div className="flex justify-between items-center text-xs mb-1">
                          <span className={isDark ? "text-zinc-500" : "text-gray-400"}>Écart</span>
                          <div className="flex items-center gap-2">
                            <span className={"text-xs px-1.5 py-0.5 rounded border font-medium " + classe}>Z={f.z_score}</span>
                            <span className="font-medium" style={{ color: couleur }}>{f.ecart_pct}%</span>
                          </div>
                        </div>
                        <div className={"w-full h-1.5 rounded-full " + (isDark ? "bg-zinc-800" : "bg-gray-100")}>
                          <div className="h-1.5 rounded-full transition-all duration-700" style={{ width: Math.min(f.ecart_pct, 100) + "%", backgroundColor: barre }} />
                        </div>
                        <p className={"text-xs mt-1 " + (isDark ? "text-zinc-600" : "text-gray-400")}>{niveauTexte}</p>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div className={"rounded-lg p-2.5 " + (isDark ? "bg-zinc-800/50" : "bg-gray-50")}>
                          <p className={"text-xs mb-0.5 " + (isDark ? "text-zinc-500" : "text-gray-400")}>Référence</p>
                          <p className={"text-xs font-semibold " + (isDark ? "text-zinc-200" : "text-gray-700")}>{fmt(f.ref_mean)} {unite}</p>
                        </div>
                        <div className={"rounded-lg p-2.5 " + (isDark ? "bg-zinc-800/50" : "bg-gray-50")}>
                          <p className={"text-xs mb-0.5 " + (isDark ? "text-zinc-500" : "text-gray-400")}>Production</p>
                          <p className={"text-xs font-semibold " + (isDark ? "text-zinc-200" : "text-gray-700")}>{fmt(f.prod_mean)} {unite}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
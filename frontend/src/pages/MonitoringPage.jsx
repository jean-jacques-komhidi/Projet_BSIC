import { useState, useEffect, useRef } from "react";
import { useTheme } from "../context/ThemeContext";
import Header from "../components/ui/Header";
import { getEtatModele, lancerRetrain, getRetrainStatus } from "../services/monitoringService";
import {
  Activity, RefreshCw, Loader2, CheckCircle2, AlertTriangle, Award, Zap, Info,
} from "lucide-react";
import { Chart, registerables } from "chart.js";

Chart.register(...registerables);

// Couleurs de l'application : chaque couleur garde un seul sens
const VERT = "#0F6E56", ORANGE = "#d97706", ROUGE = "#c0392b", BLEU = "#2E86C1", MARINE = "#0B2A4F";
const CLAIR = { [VERT]: "#34d399", [ORANGE]: "#fbbf24", [ROUGE]: "#f87171", [BLEU]: "#7cc0ea" };

const NIVEAUX = {
  stable: { libelle: "Stable", majuscules: "STABLE", couleur: VERT },
  moderee: { libelle: "Modérée", majuscules: "MODÉRÉE", couleur: ORANGE },
  forte: { libelle: "Forte", majuscules: "FORTE", couleur: ROUGE },
  inconnu: { libelle: "—", majuscules: "—", couleur: "#9ca3af" },
};
const ETATS = {
  alerte: { couleur: ROUGE, texte: "Réentraînement recommandé" },
  surveiller: { couleur: ORANGE, texte: "À surveiller : une dérive est apparue, sans atteindre la règle de réentraînement" },
  ok: { couleur: VERT, texte: "Modèle sous contrôle : aucune dérive significative, performance réelle stable" },
  insuffisant: { couleur: "#6b7280", texte: "Pas encore assez d'analyses pour surveiller le modèle" },
};
const virgule = (x, d = 2) => (x === null || x === undefined ? "—" : Number(x).toFixed(d).replace(".", ","));
const pct = (x) => (x === null || x === undefined ? "—" : `${Math.round(x)} %`);

// Graphique Chart.js générique (recréé quand la configuration change)
function Graphique({ config, hauteur }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return undefined;
    const g = new Chart(ref.current, config);
    return () => g.destroy();
  }, [config]);
  return <div style={{ position: "relative", height: hauteur }}><canvas ref={ref} /></div>;
}

function Legende({ items, isDark }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs mb-2" style={{ color: isDark ? "#a1a1aa" : "#6b7280" }}>
      {items.map(([t, c, pointille]) => (
        <span key={t} className="flex items-center gap-1.5">
          <span className="inline-block" style={pointille ? { width: 14, borderTop: `2px dashed ${c}` } : { width: 10, height: 10, borderRadius: 3, background: c }} />{t}
        </span>
      ))}
    </div>
  );
}

// Section numérotée (1 à 4)
function Section({ numero, titre, sousTitre, children, s }) {
  return (
    <div className={s.carte + " mb-5"}>
      <div className="px-5 pt-5">
        <h2 className={"text-[15px] font-semibold " + s.fort}>
          <span className="inline-grid place-items-center w-[22px] h-[22px] rounded-md text-xs font-bold mr-2 align-[1px]"
            style={{ background: BLEU + "1a", color: s.c(BLEU) }}>{numero}</span>{titre}
        </h2>
        <p className={"text-xs mt-0.5 " + s.gris}>{sousTitre}</p>
      </div>
      {children}
    </div>
  );
}

function Insuffisant({ periodes, s }) {
  return (
    <p className={"px-5 py-8 text-sm text-center " + s.texte}>
      Il faut au moins {periodes.minimum} analyses dans chaque période : {periodes.reference.analyses} en référence,
      {" "}{periodes.recente.analyses} sur les {periodes.recente.jours} derniers jours.
    </p>
  );
}

export default function MonitoringPage() {
  const { isDark } = useTheme();
  const [etat, setEtat] = useState(null);
  const [statut, setStatut] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");
  const [lancement, setLancement] = useState(false);
  const minuterie = useRef(null);

  function recuperer() {
    return getEtatModele()
      .then((e) => { setEtat(e); setStatut(e.reentrainement); setErreur(""); })
      .catch(() => setErreur("Impossible de charger le monitoring. Vérifiez que le serveur est joignable, puis actualisez."))
      .finally(() => setChargement(false));
  }
  function charger() {
    setChargement(true);
    recuperer();
  }
  useEffect(() => { recuperer(); }, []);
  useEffect(() => () => clearInterval(minuterie.current), []);

  function suivre() {
    clearInterval(minuterie.current);
    minuterie.current = setInterval(async () => {
      try {
        const s = await getRetrainStatus();
        setStatut(s);
        if (!s.running) { clearInterval(minuterie.current); charger(); }
      } catch { /* nouvel essai au prochain tour */ }
    }, 2000);
  }
  async function reentrainer() {
    setLancement(true);
    try { await lancerRetrain(); setStatut({ running: true, progress: 5, message: "Démarrage..." }); suivre(); }
    catch { setErreur("Le réentraînement n'a pas pu être lancé."); }
    finally { setLancement(false); }
  }

  const s = {
    carte: "rounded-2xl border " + (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm"),
    bordure: isDark ? "border-zinc-800" : "border-gray-100",
    gris: isDark ? "text-zinc-500" : "text-gray-400",
    texte: isDark ? "text-zinc-300" : "text-gray-600",
    fort: isDark ? "text-white" : "text-gray-800",
    tete: "text-xs uppercase tracking-wider " + (isDark ? "text-zinc-600" : "text-gray-400"),
    note: "text-xs leading-relaxed rounded-lg px-3 py-2.5 " + (isDark ? "bg-zinc-800/50 text-zinc-400" : "bg-gray-50 text-gray-500"),
    c: (couleur) => (isDark ? CLAIR[couleur] || couleur : couleur),
  };
  const axe = { color: isDark ? "#71717a" : "#9ca3af", grille: isDark ? "#27272a" : "#f3f4f6", ref: isDark ? "#52525b" : "#d1d5db",
    ligne: isDark ? "#cbd5e1" : MARINE };

  if (chargement && !etat) {
    return (<div><Header title="Monitoring" subtitle="Suivi du modèle, de la dérive et de la performance réelle" />
      <div className="text-center py-20"><Loader2 size={28} className={"animate-spin mx-auto " + s.gris} /></div></div>);
  }
  if (!etat) {
    return (<div><Header title="Monitoring" subtitle="Suivi du modèle, de la dérive et de la performance réelle" />
      <div className={s.carte + " p-8 text-center text-sm " + s.texte}>{erreur}</div></div>);
  }

  const { donnees, predictions, performance: perf, regle, modele, periodes } = etat;
  const e = ETATS[etat.etat] || ETATS.insuffisant;
  const nivDonnees = NIVEAUX[donnees.niveau] || NIVEAUX.inconnu;
  const nivPred = NIVEAUX[predictions?.niveau] || NIVEAUX.inconnu;
  const aucBasse = perf.auc !== null && modele.auc && (modele.auc - perf.auc > 0.05 || perf.auc < 0.70);
  const enCours = statut?.running;
  const dernier = statut?.last_result;
  const erreurRetrain = !enCours && statut?.message?.startsWith("Erreur");
  const recent = etat.etat === "alerte" || donnees.niveau !== "stable" ? ORANGE : BLEU;
  const insuffisant = etat.etat === "insuffisant";
  const optionsBase = (y) => ({ responsive: true, maintainAspectRatio: false, animation: { duration: 500 },
    plugins: { legend: { display: false } },
    scales: { x: { grid: { display: false }, ticks: { color: axe.color, font: { size: 10 } } },
      y: { grid: { color: axe.grille }, ticks: { color: axe.color, font: { size: 10 }, ...y } } } });

  const d = donnees.detail;
  const cfgDetail = d && { type: "bar", data: { labels: d.tranches, datasets: [
    { data: d.reference, backgroundColor: axe.ref, borderRadius: 3 }, { data: d.recent, backgroundColor: recent, borderRadius: 3 }] },
    options: optionsBase({ callback: (v) => v + " %" }) };
  const cfgScores = predictions && { type: "bar", data: {
    labels: Array.from({ length: 20 }, (_, i) => (i % 2 === 0 ? i * 5 + " %" : "")), datasets: [
      { data: predictions.reference, backgroundColor: axe.ref, barPercentage: 1, categoryPercentage: 0.9 },
      { data: predictions.recent, backgroundColor: recent + "cc", barPercentage: 1, categoryPercentage: 0.9 }] },
    options: optionsBase({ callback: (v) => v + " %" }) };
  const cfgRefus = predictions && { type: "line", data: { labels: predictions.semaines.map((w) => w.debut), datasets: [
    { data: predictions.semaines.map((w) => w.taux_refus), borderColor: axe.ligne, backgroundColor: axe.ligne, tension: 0.3, pointRadius: 2, spanGaps: true },
    { data: predictions.semaines.map(() => predictions.taux_refus_reference), borderColor: axe.ref, borderDash: [4, 4], pointRadius: 0 }] },
    options: optionsBase({ callback: (v) => v + " %" }) };
  const aucs = perf.mois.map((m) => m.auc).filter((a) => a !== null);
  const aucMin = Math.min(0.5, Math.floor((Math.min(...aucs, 1) - 0.05) * 10) / 10);
  const aucMax = Math.max(0.9, Math.ceil((Math.max(...aucs, 0) + 0.02) * 10) / 10);
  const cfgAuc = { type: "line", data: { labels: perf.mois.map((m) => `${m.mois} (${m.issues})`), datasets: [
    { data: perf.mois.map((m) => m.auc), borderColor: axe.ligne, tension: 0.3, pointRadius: 4, spanGaps: true,
      pointBackgroundColor: perf.mois.map((m) => (m.auc !== null && m.auc < 0.7 ? ROUGE : axe.ligne)) },
    { data: perf.mois.map(() => 0.7), borderColor: ROUGE, borderDash: [4, 4], pointRadius: 0 }] },
    options: { ...optionsBase({ callback: (v) => virgule(v) }), scales: { ...optionsBase({}).scales,
      y: { min: aucMin, max: Math.min(aucMax, 1), grid: { color: axe.grille }, ticks: { color: axe.color, font: { size: 10 }, callback: (v) => virgule(v) } } } } };
  const cfgDefaut = { type: "bar", data: { labels: perf.mois.map((m) => m.mois), datasets: [
    { data: perf.mois.map((m) => m.defaut_predit), backgroundColor: BLEU, borderRadius: 3 },
    { data: perf.mois.map((m) => m.defaut_constate), backgroundColor: ROUGE, borderRadius: 3 }] },
    options: optionsBase({ callback: (v) => v + " %" }) };

  const deuxColonnes = "grid grid-cols-1 lg:grid-cols-[1.15fr_1fr] " + (isDark ? "lg:divide-x divide-zinc-800" : "lg:divide-x divide-gray-100");

  return (
    <div>
      <Header title="Monitoring" subtitle="Suivi du modèle, de la dérive et de la performance réelle" />

      {/* Barre supérieure */}
      <div className="flex items-center justify-between mb-5 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Activity size={15} className={s.gris} />
          <span className={"font-semibold text-sm " + s.fort}>Tableau de monitoring</span>
          {modele.version && <span className={"text-xs px-2 py-0.5 rounded-full border font-medium " + (isDark ? "border-zinc-700 text-zinc-500" : "border-gray-200 text-gray-400")}>v{modele.version}</span>}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={charger} className={"flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border transition " +
            (isDark ? "border-zinc-800 text-zinc-400 hover:bg-zinc-800" : "border-gray-200 text-gray-500 hover:bg-gray-50")}>
            <RefreshCw size={13} className={chargement ? "animate-spin" : ""} /> Actualiser
          </button>
          <button onClick={reentrainer} disabled={enCours || lancement}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
            style={{ backgroundColor: BLEU }}>
            {enCours || lancement ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />} Réentraîner le modèle
          </button>
        </div>
      </div>

      {erreur && <div className="mb-4 rounded-xl border px-4 py-3 text-sm" style={{ borderColor: ROUGE + "55", color: ROUGE, background: ROUGE + "0d" }}>{erreur}</div>}

      {/* Progression et résultat du réentraînement */}
      {enCours && (
        <div className={s.carte + " p-4 mb-5"}>
          <div className="flex items-center justify-between mb-2">
            <span className={"flex items-center gap-2 text-xs font-medium " + s.fort}><Loader2 size={13} className="animate-spin" style={{ color: BLEU }} /> Réentraînement en cours</span>
            <span className="text-xs font-semibold" style={{ color: BLEU }}>{statut.progress || 0} %</span>
          </div>
          <div className={"w-full h-1.5 rounded-full mb-2 " + (isDark ? "bg-zinc-800" : "bg-gray-100")}>
            <div className="h-1.5 rounded-full transition-all duration-500" style={{ width: (statut.progress || 0) + "%", backgroundColor: BLEU }} />
          </div>
          <p className={"text-xs " + s.gris}>{statut.message}</p>
        </div>
      )}
      {erreurRetrain && (
        <div className="mb-5 rounded-xl border px-4 py-3 text-sm" style={{ borderColor: ORANGE + "66", color: s.c(ORANGE), background: ORANGE + "0f" }}>
          Réentraînement impossible. {statut.message.replace(/^Erreur : /, "")}
        </div>
      )}
      {!enCours && dernier && (
        <div className="rounded-2xl border p-4 mb-5" style={{ borderColor: (dernier.improved ? VERT : BLEU) + "55", background: (dernier.improved ? VERT : BLEU) + "0d" }}>
          <p className="flex items-center gap-2 text-xs font-semibold mb-3" style={{ color: s.c(dernier.improved ? VERT : BLEU) }}>
            {dernier.improved ? <CheckCircle2 size={14} /> : <Info size={14} />}
            {dernier.improved ? `${dernier.best_model} mis en service : il fait mieux que le modèle précédent`
              : `${dernier.best_model} non retenu : il ne fait pas mieux, le modèle en service est conservé`}
          </p>
          <div className="grid grid-cols-3 gap-3">
            {[["AUC du modèle en service", virgule(dernier.old_auc, 3)], ["AUC du candidat", virgule(dernier.new_auc, 3)], ["Comparés sur", dernier.jeu_comparaison]].map(([t, v]) => (
              <div key={t} className={"rounded-lg p-2.5 " + (isDark ? "bg-zinc-800/50" : "bg-white/70")}>
                <p className={"text-xs mb-0.5 " + s.gris}>{t}</p><p className={"text-sm font-semibold " + s.fort}>{v}</p>
              </div>
            ))}
          </div>
          <p className={"text-xs mt-3 " + s.gris}>{dernier.timestamp}</p>
        </div>
      )}

      {/* Bandeau d'état */}
      <div className="flex items-center gap-3 px-4 py-3 rounded-xl border mb-5 flex-wrap" style={{ borderColor: e.couleur + "55", background: e.couleur + (isDark ? "14" : "0b") }}>
        <span className="w-2 h-2 rounded-full" style={{ background: e.couleur }} />
        <span className="text-xs font-medium" style={{ color: s.c(e.couleur) }}>
          {e.texte}{etat.etat === "alerte" && ` : ${regle.atteintes} condition${regle.atteintes > 1 ? "s" : ""} sur 3 atteinte${regle.atteintes > 1 ? "s" : ""}`}
        </span>
        <span className={"text-xs ml-auto " + s.gris}>
          Référence : {periodes.reference.analyses} analyses{periodes.reference.debut ? ` (${periodes.reference.debut} au ${periodes.reference.fin})` : ""}, récent : {periodes.recente.analyses} analyses sur {periodes.recente.jours} jours
        </span>
      </div>

      {/* 4 KPI */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        {[
          ["AUC à l'entraînement", virgule(modele.auc, 3), null, modele.algorithme ? `${modele.algorithme}, v${modele.version}` : "Aucun modèle enregistré"],
          ["AUC réelle", virgule(perf.auc), perf.auc === null ? null : aucBasse ? ROUGE : VERT,
            perf.issues >= perf.issues_minimum ? `Sur ${perf.issues} crédits à l'issue connue` : `${perf.issues} issues sur ${perf.issues_minimum} nécessaires`],
          ["Dérive des prédictions", predictions ? `PSI ${virgule(predictions.psi)}` : "—", predictions ? nivPred.couleur : null,
            predictions ? `Taux de refus : ${pct(predictions.taux_refus_reference)} → ${pct(predictions.taux_refus_recent)}` : "Pas assez d'analyses"],
          ["Statut dérive", nivDonnees.majuscules, donnees.niveau === "inconnu" ? null : nivDonnees.couleur,
            donnees.variables.length ? `PSI max ${virgule(donnees.psi_max)}, ${donnees.variables.length} variables` : "Pas assez d'analyses"],
        ].map(([t, v, c, sous]) => (
          <div key={t} className={s.carte + " p-4"}>
            <p className={"text-xs mb-1 " + s.gris}>{t}</p>
            <p className={"text-xl font-bold " + (c ? "" : s.fort)} style={c ? { color: s.c(c) } : {}}>{v}</p>
            <p className={"text-xs mt-0.5 " + s.gris}>{sous}</p>
          </div>
        ))}
      </div>

      {/* Résumés */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-5">
        <div className={s.carte + " p-4 flex items-center justify-between"}>
          <div className="flex items-center gap-2.5">
            <div className={"w-9 h-9 rounded-lg flex items-center justify-center " + (isDark ? "bg-zinc-800" : "bg-gray-100")}><Award size={16} className="text-amber-500" /></div>
            <div><p className={"text-xs " + s.gris}>Modèle en production</p><p className={"text-sm font-semibold " + s.fort}>{modele.algorithme || "—"}{modele.version ? ` (v${modele.version})` : ""}</p></div>
          </div>
          <div className="text-right"><p className={"text-lg font-bold " + s.fort}>{virgule(modele.auc, 3)}</p><p className={"text-xs " + s.gris}>AUC-ROC à l'entraînement</p></div>
        </div>
        <div className={s.carte + " p-4 flex items-center justify-between"}>
          <div className="flex items-center gap-2.5">
            <div className={"w-9 h-9 rounded-lg flex items-center justify-center " + (isDark ? "bg-zinc-800" : "bg-gray-100")}>
              {regle.reentrainement_recommande ? <AlertTriangle size={16} style={{ color: s.c(ROUGE) }} /> : <CheckCircle2 size={16} style={{ color: s.c(VERT) }} />}
            </div>
            <div><p className={"text-xs " + s.gris}>Faut-il réentraîner ?</p>
              <p className="text-sm font-semibold" style={{ color: s.c(regle.reentrainement_recommande ? ROUGE : VERT) }}>
                {regle.reentrainement_recommande ? "Oui, réentraînement recommandé" : "Non, pas pour l'instant"}</p></div>
          </div>
          <div className="text-right"><p className={"text-lg font-bold " + s.fort}>{regle.atteintes} / 3</p><p className={"text-xs " + s.gris}>conditions atteintes</p></div>
        </div>
      </div>

      {/* Versions du modèle */}
      <div className="mb-6">
        <div className="flex items-baseline justify-between mb-3 gap-3 flex-wrap">
          <p className={s.tete}>Détail des versions du modèle</p>
          <p className={"text-xs " + s.gris}>Un nouveau modèle ne remplace l'actuel que s'il fait mieux sur les mêmes données</p>
        </div>
        <div className={s.carte + " overflow-x-auto"}>
          <table className="w-full min-w-[560px]">
            <thead><tr className={"border-b " + s.bordure}>
              {["Modèle", "Version", "AUC entraînement", "AUC réelle", "Statut"].map((h, i) => (
                <th key={h} className={(i < 2 ? "text-left " : "text-center ") + "py-2.5 " + (i === 0 ? "px-4 " : "") + s.tete}>{h}</th>
              ))}
            </tr></thead>
            <tbody>
              {etat.versions.map((v) => {
                const st = { production: ["Actif", VERT], retire: ["Retiré", "#6b7280"], rejete: ["Non retenu", "#6b7280"] }[v.statut] || ["—", "#6b7280"];
                return (
                  <tr key={v.version} className={"border-t " + (isDark ? "border-zinc-800/50" : "border-gray-50")}>
                    <td className="py-3 px-4"><span className={"text-xs font-semibold " + (isDark ? "text-zinc-200" : "text-gray-700")}>{v.algorithme}</span>
                      {v.statut === "production" && <span className={"ml-2 text-xs px-1.5 py-0.5 rounded border font-medium " + (isDark ? "border-amber-900 text-amber-400" : "border-amber-200 text-amber-600")}>En production</span>}</td>
                    <td className={"py-3 text-xs " + s.texte}>v{v.version}{v.date ? `, ${v.date}` : ""}</td>
                    <td className={"py-3 text-center text-xs " + s.texte}>{virgule(v.auc, 3)}</td>
                    <td className="py-3 text-center text-xs font-semibold" style={{ color: v.auc_reelle === null ? undefined : s.c(v.auc_reelle < 0.7 ? ROUGE : VERT) }}>{virgule(v.auc_reelle)}</td>
                    <td className="py-3 text-center"><span className="text-xs px-1.5 py-0.5 rounded border" style={{ color: s.c(st[1]), borderColor: st[1] + "55" }}>{st[0]}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 1. Données */}
      <Section s={s} numero="1" titre="Les données : les dossiers ressemblent-ils à ceux de référence ?"
        sousTitre="Indice de stabilité (PSI) de chaque variable entre la référence et les 30 derniers jours. Repères : 0,10 et 0,25. Une dérive n'est retenue que si elle ne peut pas s'expliquer par le hasard.">
        {insuffisant ? <Insuffisant periodes={periodes} s={s} /> : (
          <div className={deuxColonnes}>
            <div className="px-5 py-4 overflow-x-auto">
              <table className="w-full">
                <thead><tr>{["Variable", "PSI", "Dérive"].map((h) => <th key={h} className={"text-left text-[11px] font-medium py-2 " + s.gris}>{h}</th>)}</tr></thead>
                <tbody>
                  {donnees.variables.map((v) => {
                    const n = NIVEAUX[v.niveau];
                    const c = v.niveau === "stable" ? VERT : n.couleur;
                    return (
                      <tr key={v.variable} className={"border-t " + s.bordure + (d && v.variable === d.variable ? (isDark ? " bg-sky-950/30" : " bg-sky-50/60") : "")}>
                        <td className={"py-2 pr-2 text-sm " + s.fort}>{v.libelle}</td>
                        <td className="py-2">
                          <div className="flex items-center gap-2">
                            <div className={"relative w-24 h-2 rounded-full " + (isDark ? "bg-zinc-800" : "bg-gray-100")}>
                              <div className="absolute inset-y-0 left-0 rounded-full" style={{ width: Math.min(v.psi / 0.4, 1) * 100 + "%", background: v.significatif ? c : axe.ref }} />
                              <div className="absolute -top-0.5 -bottom-0.5 w-px bg-gray-400" style={{ left: "25%" }} />
                              <div className="absolute -top-0.5 -bottom-0.5 w-px bg-gray-400" style={{ left: "62.5%" }} />
                            </div>
                            <span className="text-sm font-semibold w-10 text-right" style={{ color: v.significatif ? s.c(c) : undefined }}>{virgule(v.psi)}</span>
                          </div>
                        </td>
                        <td className="py-2">
                          <span className="text-xs px-2 py-0.5 rounded-full border font-medium" style={{ color: s.c(c), borderColor: c + "55" }}>{n.libelle}</span>
                          {!v.significatif && v.psi >= 0.1 && <span className={"block text-[11px] mt-0.5 " + s.gris}>écart dû au hasard possible</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {d && (
              <div className="px-5 py-4">
                <p className={"text-sm font-semibold " + s.fort}>{d.libelle} : répartition des dossiers</p>
                <p className={"text-xs mt-0.5 mb-2 " + s.gris}>Part des dossiers par tranche. Les tranches contiennent chacune la même part des dossiers de référence.</p>
                <Legende isDark={isDark} items={[["Référence", axe.ref], ["30 derniers jours", recent]]} />
                <Graphique config={cfgDetail} hauteur={210} />
                <p className={s.note + " mt-3"}>{donnees.phrase}</p>
              </div>
            )}
          </div>
        )}
      </Section>

      {/* 2. Prédictions */}
      <Section s={s} numero="2" titre="Les prédictions : le modèle répond-il comme avant ?"
        sousTitre="Répartition des probabilités de défaut calculées, et taux de refus semaine par semaine.">
        {insuffisant || !predictions ? <Insuffisant periodes={periodes} s={s} /> : (
          <div className={deuxColonnes}>
            <div className="px-5 py-4">
              <Legende isDark={isDark} items={[["Référence", axe.ref], ["30 derniers jours", recent]]} />
              <Graphique config={cfgScores} hauteur={190} />
              <p className={"text-xs mt-2 " + s.gris}>PSI des scores : {virgule(predictions.psi)} ({nivPred.libelle.toLowerCase()}). Le seuil de refus est à 70 %.</p>
            </div>
            <div className="px-5 py-4">
              <Legende isDark={isDark} items={[["Taux de refus par semaine", axe.ligne], [`Taux de référence (${pct(predictions.taux_refus_reference)})`, axe.ref, true]]} />
              <Graphique config={cfgRefus} hauteur={190} />
            </div>
          </div>
        )}
      </Section>

      {/* 3. Performance réelle */}
      <Section s={s} numero="3" titre="La performance réelle : le modèle se trompe-t-il plus ?"
        sousTitre="Calculée sur les crédits accordés dont l'issue est connue, par mois d'octroi. Les crédits trop récents n'ont pas encore d'issue.">
        <div className={deuxColonnes}>
          <div className="px-5 py-4">
            <Legende isDark={isDark} items={[["AUC sur les issues réelles (nombre d'issues)", axe.ligne], ["Seuil d'alerte (0,70)", ROUGE, true]]} />
            <Graphique config={cfgAuc} hauteur={200} />
          </div>
          <div className="px-5 py-4">
            <Legende isDark={isDark} items={[["Défaut prédit", BLEU], ["Défaut constaté", ROUGE]]} />
            <Graphique config={cfgDefaut} hauteur={200} />
          </div>
        </div>
        <div className="px-5 pb-5">
          <p className={s.note}>
            {perf.issues} issues connues sur les 6 derniers mois{perf.issues < perf.issues_minimum ? ` (${perf.issues_minimum} nécessaires pour juger la performance)` : ""}, {perf.issues_en_attente} crédits attendent encore la leur.
            {" "}Limites : l'issue d'un crédit n'est connue qu'après plusieurs mois, et seulement pour les crédits accordés. On ne saura jamais si un client refusé aurait remboursé (biais de sélection).
          </p>
        </div>
      </Section>

      {/* 4. Règle de réentraînement */}
      <Section s={s} numero="4" titre="Faut-il réentraîner le modèle ?"
        sousTitre={`Règle fixée à l'avance : le réentraînement est recommandé dès qu'une condition est atteinte. Les conditions de performance demandent au moins ${perf.issues_minimum} issues réelles.`}>
        <div className={deuxColonnes}>
          <div className="px-5 py-4 space-y-2.5">
            {regle.conditions.map((c) => (
              <div key={c.titre} className={"grid grid-cols-[26px_1fr_auto] gap-3 items-center rounded-xl border px-3.5 py-3 " + s.bordure}>
                <span className="w-[26px] h-[26px] rounded-full grid place-items-center text-xs font-bold"
                  style={{ background: (c.atteinte ? ROUGE : VERT) + "1a", color: s.c(c.atteinte ? ROUGE : VERT) }}>{c.atteinte ? "!" : "✓"}</span>
                <p className={"text-sm " + s.fort}>{c.titre}<span className={"block text-xs mt-0.5 " + s.gris}>{c.detail}</span></p>
                <span className="text-xs px-2 py-0.5 rounded-full border font-medium whitespace-nowrap"
                  style={{ color: s.c(c.atteinte ? ROUGE : VERT), borderColor: (c.atteinte ? ROUGE : VERT) + "55" }}>{c.atteinte ? "Atteint" : "Non atteint"}</span>
              </div>
            ))}
          </div>
          <div className="px-5 py-4 flex flex-col gap-3">
            <div className="rounded-xl border p-3.5 flex items-center justify-between gap-3"
              style={{ borderColor: (regle.reentrainement_recommande ? ROUGE : VERT) + "44", background: (regle.reentrainement_recommande ? ROUGE : VERT) + "0d" }}>
              <p className={"text-sm " + s.texte}>
                <b className="block text-sm" style={{ color: s.c(regle.reentrainement_recommande ? ROUGE : VERT) }}>
                  {regle.reentrainement_recommande ? "Réentraînement recommandé" : "Pas de réentraînement nécessaire"}</b>
                {regle.atteintes} condition{regle.atteintes > 1 ? "s" : ""} sur 3 atteinte{regle.atteintes > 1 ? "s" : ""}.
              </p>
              <button onClick={reentrainer} disabled={enCours || lancement}
                className={"px-3.5 py-2 rounded-lg text-sm font-medium whitespace-nowrap disabled:opacity-50 " + (regle.reentrainement_recommande ? "text-white" : "border " + (isDark ? "border-zinc-700 text-zinc-300" : "border-gray-200 text-gray-700"))}
                style={regle.reentrainement_recommande ? { background: BLEU } : {}}>
                Lancer un réentraînement
              </button>
            </div>
            <p className={s.note}>
              La règle alerte, l'administrateur décide. Après un réentraînement, le candidat est comparé au modèle en service sur les mêmes données :
              il ne le remplace que s'il fait mieux (voir le tableau des versions). Les alertes sont aussi envoyées dans les notifications.
              {" "}Dernier calcul : {etat.date_calcul}.
            </p>
          </div>
        </div>
      </Section>
    </div>
  );
}


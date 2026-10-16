// Page « Détail de l'analyse » : parcours du client, décision, dossier,
// facteurs déterminants, simulateur, recommandations et issue du crédit.
import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import ConfirmationSuppression from "../components/ui/ConfirmationSuppression";
import {
  ArrowLeft, Loader2, FileDown, MessageSquare, CheckCircle2, XCircle, ThumbsUp, ThumbsDown,
  Clock, Ban, TrendingUp, TrendingDown, Minus, AlertTriangle, SlidersHorizontal, RotateCcw, ArrowRight, Trash2,
} from "lucide-react";
import Header from "../components/ui/Header";
import { getAnalyse, renseignerResultat, telechargerPdf, simulerAnalyse, supprimerAnalyse } from "../services/analyseService";

const BLEU = "#2E86C1", VERT = "#0F6E56", ORANGE = "#d97706", ROUGE = "#c0392b";
const CLAIR = { [VERT]: "#34d399", [ORANGE]: "#fbbf24", [ROUGE]: "#f87171", [BLEU]: "#7cc0ea" };
const DELAI = 30;

const versDate = (d) => new Date(String(d).endsWith("Z") ? d : d + "Z");
const fmt = (d, o) => versDate(d).toLocaleString("fr-FR", { timeZone: "Africa/Ndjamena", ...o });
const dateLongue = (d) => fmt(d, { day: "numeric", month: "long", year: "numeric" });
const dateCourte = (d) => fmt(d, { day: "2-digit", month: "2-digit", year: "numeric" });
const moisAnnee = (d) => fmt(d, { month: "long", year: "numeric" });
const heure = (d) => fmt(d, { hour: "2-digit", minute: "2-digit" });
const pct = (p, dec = 0) => (p * 100).toLocaleString("fr-FR", { minimumFractionDigits: dec, maximumFractionDigits: dec }) + " %";
const fcfa = (n) => (n ? Number(n).toLocaleString("fr-FR", { maximumFractionDigits: 0 }) + " FCFA" : "—");
const teinte = (p) => (p < 0.4 ? VERT : p < 0.7 ? ORANGE : ROUGE);
const NIVEAU = { faible: "faible", moyen: "moyen", eleve: "élevé" };

function styles(isDark) {
  return {
    carte: "rounded-2xl border " + (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm"),
    titre: "font-semibold text-sm " + (isDark ? "text-white" : "text-gray-800"),
    sous: "text-xs mt-0.5 " + (isDark ? "text-zinc-500" : "text-gray-400"),
    libelle: "text-xs " + (isDark ? "text-zinc-500" : "text-gray-400"),
    valeur: "text-sm font-medium " + (isDark ? "text-zinc-100" : "text-gray-800"),
    texte: "text-sm leading-relaxed " + (isDark ? "text-zinc-300" : "text-gray-600"),
    bordure: isDark ? "border-zinc-800" : "border-gray-100",
    fond: isDark ? "bg-zinc-800/40" : "bg-gray-50",
    bouton: "flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium border transition " +
      (isDark ? "border-zinc-700 text-zinc-300 hover:bg-zinc-800" : "border-gray-200 text-gray-700 bg-white hover:bg-gray-50"),
    c: (couleur) => (isDark ? CLAIR[couleur] || couleur : couleur),
  };
}

function Pastille({ couleur, isDark, children, grande }) {
  return (
    <span className={"inline-flex items-center gap-1 rounded-full border font-medium whitespace-nowrap " +
      (grande ? "text-sm px-3 py-1" : "text-xs px-2 py-0.5")}
      style={{ color: isDark ? CLAIR[couleur] : couleur, borderColor: couleur + "55", backgroundColor: couleur + (isDark ? "26" : "0d") }}>
      {children}
    </span>
  );
}

// Échelle horizontale du risque : zones 0-40-70-100 et repère de la probabilité
function EchelleRisque({ proba, isDark }) {
  const p = Math.min(Math.max(proba, 0), 1) * 100;
  const zone = (de, a, couleur) => (
    <div className="absolute inset-y-0" style={{ left: de + "%", width: a - de + "%", background: couleur + (isDark ? "40" : "26") }} />
  );
  return (
    <div className="pt-7 pb-9">
      <div className="relative h-2.5 rounded-full overflow-visible">
        <div className="absolute inset-0 rounded-full overflow-hidden">{zone(0, 40, VERT)}{zone(40, 70, ORANGE)}{zone(70, 100, ROUGE)}</div>
        <div className="absolute inset-y-0 left-0 rounded-full" style={{ width: p + "%", background: teinte(proba) }} />
        <div className="absolute -top-7 -translate-x-1/2 text-xs font-semibold whitespace-nowrap" style={{ left: p + "%", color: isDark ? CLAIR[teinte(proba)] : teinte(proba) }}>
          {pct(proba, 1)}
        </div>
        <div className="absolute -top-1.5 -translate-x-1/2 w-1 h-5.5 rounded-full" style={{ left: p + "%", height: 22, background: isDark ? "#fafafa" : "#1f2937" }} />
        {[[40, "40 %"], [70, "70 % : refus"]].map(([v, t]) => (
          <div key={v} className={"absolute top-4 -translate-x-1/2 text-[11px] whitespace-nowrap " + (isDark ? "text-zinc-500" : "text-gray-400")} style={{ left: v + "%" }}>
            <div className={"w-px h-1.5 mx-auto mb-0.5 " + (isDark ? "bg-zinc-600" : "bg-gray-300")} />{t}
          </div>
        ))}
      </div>
    </div>
  );
}

function issueDe(a, maintenant) {
  if (a.decision !== "ACCORDE") return null;
  if (a.resultat_reel) return a.resultat_reel;
  return (maintenant - versDate(a.date || a.date_analyse)) / 86400000 > DELAI ? "a_renseigner" : "en_cours";
}
function IssuePastille({ a, maintenant, isDark }) {
  const i = issueDe(a, maintenant);
  if (i === "rembourse") return <Pastille couleur={VERT} isDark={isDark}>Remboursé</Pastille>;
  if (i === "defaut") return <Pastille couleur={ROUGE} isDark={isDark}>Défaut</Pastille>;
  if (i === "a_renseigner") return <Pastille couleur={ORANGE} isDark={isDark}>À renseigner</Pastille>;
  if (i === "en_cours") return <span className={"text-xs " + (isDark ? "text-zinc-500" : "text-gray-400")}>En cours</span>;
  return <span className={isDark ? "text-zinc-600" : "text-gray-300"}>—</span>;
}

// Bloc « Issue du crédit » (confirmation, correction, rien pour un refus)
function BlocIssue({ analyse, estAdmin, maintenant, isDark, onMaj, compact }) {
  const s = styles(isDark);
  const [choix, setChoix] = useState(null);
  const [correction, setCorrection] = useState(false);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState("");
  const accorde = analyse.decision === "ACCORDE";
  const jours = Math.floor((maintenant - versDate(analyse.date_analyse)) / 86400000);

  async function confirmer() {
    setEnvoi(true); setErreur("");
    try { await renseignerResultat(analyse.id, choix); setChoix(null); setCorrection(false); await onMaj(); }
    catch (e) { setErreur(e?.response?.data?.detail || "Enregistrement impossible. Réessayez."); }
    finally { setEnvoi(false); }
  }

  let contenu;
  if (!accorde) contenu = <p className={"flex items-center gap-2 " + s.texte}><Ban size={16} /> Crédit refusé : aucune issue à suivre.</p>;
  else if (analyse.resultat_reel && !correction) contenu = (
    <div className="flex items-center gap-3">
      {analyse.resultat_reel === "rembourse"
        ? <Pastille grande couleur={VERT} isDark={isDark}><CheckCircle2 size={15} /> Crédit remboursé</Pastille>
        : <Pastille grande couleur={ROUGE} isDark={isDark}><XCircle size={15} /> Crédit en défaut</Pastille>}
      {estAdmin && <button onClick={() => setCorrection(true)} className="text-xs underline" style={{ color: BLEU }}>Corriger</button>}
    </div>
  );
  else if (!estAdmin) contenu = <p className={"flex items-center gap-2 " + s.texte}><Clock size={16} /> Issue pas encore connue. Seul un administrateur peut la renseigner.</p>;
  else if (choix) contenu = (
    <div>
      <p className={s.texte}>Enregistrer ce crédit comme <b style={{ color: s.c(choix === "rembourse" ? VERT : ROUGE) }}>{choix === "rembourse" ? "remboursé" : "en défaut"}</b> ?</p>
      <div className="flex gap-2 mt-3">
        <button onClick={confirmer} disabled={envoi} className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-60"
          style={{ background: choix === "rembourse" ? VERT : ROUGE }}>{envoi && <Loader2 size={15} className="animate-spin" />} Confirmer</button>
        <button onClick={() => setChoix(null)} className={s.bouton}>Annuler</button>
      </div>
    </div>
  );
  else contenu = (
    <div>
      {jours < DELAI && <p className={s.libelle + " mb-3"}>Accordé il y a {jours} jour{jours > 1 ? "s" : ""} : l'issue est en général connue après {DELAI} jours.</p>}
      <div className="flex flex-wrap gap-2">
        <button onClick={() => setChoix("rembourse")} className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium border"
          style={{ borderColor: VERT, color: s.c(VERT) }}><ThumbsUp size={15} /> Remboursé</button>
        <button onClick={() => setChoix("defaut")} className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium border"
          style={{ borderColor: ROUGE, color: s.c(ROUGE) }}><ThumbsDown size={15} /> En défaut</button>
        {correction && <button onClick={() => setCorrection(false)} className={s.bouton}>Annuler</button>}
      </div>
    </div>
  );

  return (
    <div className={compact ? "" : s.carte + " p-5"}>
      <p className={s.titre}>Issue du crédit</p>
      {!compact && <p className={s.sous}>Sert à mesurer la justesse du modèle et à le réentraîner.</p>}
      <div className="mt-3">{contenu}</div>
      {erreur && <p className="text-xs mt-2" style={{ color: ROUGE }}>{erreur}</p>}
    </div>
  );
}

function Actions({ analyse, isDark, estAdmin, onSupprimer }) {
  const s = styles(isDark);
  const navigate = useNavigate();
  const [pdf, setPdf] = useState(false);
  async function exporter() {
    setPdf(true);
    try {
      const url = window.URL.createObjectURL(await telechargerPdf(analyse.id));
      const a = document.createElement("a"); a.href = url; a.download = `fiche_decision_${analyse.id}.pdf`; a.click();
      window.URL.revokeObjectURL(url);
    } finally { setPdf(false); }
  }
  return (
    <div className="flex items-center gap-2">
      {estAdmin && (
        <button onClick={onSupprimer} aria-label="Supprimer l'analyse" title="Supprimer l'analyse"
          className={"p-2 rounded-lg border transition " + (isDark ? "border-zinc-700 text-zinc-400 hover:text-red-400 hover:border-red-900" : "border-gray-200 text-gray-500 bg-white hover:text-red-700 hover:border-red-200")}>
          <Trash2 size={17} />
        </button>
      )}
      <button onClick={exporter} className={s.bouton}>{pdf ? <Loader2 size={16} className="animate-spin" /> : <FileDown size={16} />} Fiche PDF</button>
      <button onClick={() => navigate(`/assistant?analyse=${analyse.id}`)} className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium text-white hover:opacity-90"
        style={{ background: BLEU }}><MessageSquare size={16} /> Interroger CrediBot</button>
    </div>
  );
}

function Retour({ isDark }) {
  const navigate = useNavigate();
  return (
    <button onClick={() => navigate("/historique")} aria-label="Retour à l'historique" title="Retour à l'historique"
      className={"p-2 rounded-lg border transition " + (isDark ? "border-zinc-800 text-zinc-400 hover:bg-zinc-800" : "border-gray-200 text-gray-500 bg-white hover:bg-gray-50")}>
      <ArrowLeft size={18} />
    </button>
  );
}

function ColonneFacteurs({ titre, liste, couleur, Icone, vide, part, isDark }) {
  const s = styles(isDark);
  const impact = (p) => (p >= 0.25 ? "fort" : p >= 0.12 ? "moyen" : "faible");
  return (
    <div>
      <p className="flex items-center gap-1.5 text-xs font-semibold mb-3" style={{ color: s.c(couleur) }}>
        <Icone size={14} /> {titre}
      </p>
      {liste.length === 0 ? <p className={s.libelle}>{vide}</p> : (
        <div className="space-y-2">
          {liste.map((f) => (
            <div key={f.libelle} className={"rounded-xl border px-3.5 py-3 " + s.bordure}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className={"text-sm font-medium " + (isDark ? "text-zinc-100" : "text-gray-800")}>{f.libelle}</p>
                  <p className={s.libelle}>
                    Valeur du dossier : <span className={isDark ? "text-zinc-300" : "text-gray-600"}>{f.valeur}</span>
                    {f.appreciation && <span className="ml-1.5 font-medium" style={{ color: s.c(couleur) }}>({f.appreciation})</span>}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-sm font-semibold" style={{ color: s.c(couleur) }}>{pct(part(f))}</p>
                  <p className={s.libelle}>impact {impact(part(f))}</p>
                </div>
              </div>
              <div className={"h-1.5 rounded-full mt-2.5 " + (isDark ? "bg-zinc-800" : "bg-gray-100")}>
                <div className="h-full rounded-full" style={{ width: part(f) * 100 + "%", background: couleur }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Alerte si le risque monte sur au moins trois analyses consécutives
function AlerteTendance({ historique, idCourant, isDark }) {
  const jusquIci = historique.slice(0, historique.findIndex((a) => a.id === idCourant) + 1);
  const derniers = jusquIci.slice(-3);
  const hausse = derniers.length === 3 && derniers.every((a, i) => i === 0 || a.probabilite_defaut - derniers[i - 1].probabilite_defaut >= 0.03);
  if (!hausse) return null;
  return (
    <div className="flex items-start gap-3 rounded-xl border px-4 py-3 mb-5"
      style={{ borderColor: ORANGE + "66", background: ORANGE + (isDark ? "1f" : "12"), color: isDark ? CLAIR[ORANGE] : "#92400e" }}>
      <AlertTriangle size={18} className="shrink-0 mt-0.5" />
      <p className="text-sm">
        <b>Risque en hausse continue</b> sur les {derniers.length} dernières analyses
        ({derniers.map((a) => pct(a.probabilite_defaut)).join(", puis ")}).
        Vérifiez la situation du client avant tout nouvel engagement.
      </p>
    </div>
  );
}

// Ce qui a changé depuis l'analyse précédente du client
function Changements({ changements, probaActuelle, isDark }) {
  const s = styles(isDark);
  if (!changements) return null;
  const lignes = [...changements.lignes].sort((a, b) => b.defavorable - a.defavorable);
  const ecart = Math.round((probaActuelle - changements.probabilite_defaut) * 100);
  return (
    <div className={s.carte + " p-5 mb-5"}>
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <p className={s.titre}>Ce qui a changé depuis l'analyse du {dateCourte(changements.date)}</p>
          <p className={s.sous}>Éléments du dossier qui ont évolué de façon notable</p>
        </div>
        <p className="text-sm">
          <span className={isDark ? "text-zinc-400" : "text-gray-500"}>Risque : </span>
          <b style={{ color: s.c(teinte(changements.probabilite_defaut)) }}>{pct(changements.probabilite_defaut)}</b>
          <ArrowRight size={14} className={"inline mx-1.5 " + (isDark ? "text-zinc-500" : "text-gray-400")} />
          <b style={{ color: s.c(teinte(probaActuelle)) }}>{pct(probaActuelle)}</b>
          <span className="ml-2 text-xs font-medium" style={{ color: s.c(ecart > 0 ? ROUGE : ecart < 0 ? VERT : BLEU) }}>
            ({ecart > 0 ? "+" : ""}{ecart} points)
          </span>
        </p>
      </div>
      {lignes.length === 0 ? (
        <p className={s.texte + " mt-3"}>Aucun changement notable dans le dossier.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 mt-4">
          {lignes.map((l) => {
            const couleur = l.defavorable ? ROUGE : VERT;
            const Icone = l.sens === "hausse" ? TrendingUp : TrendingDown;
            return (
              <div key={l.libelle} className={"rounded-xl border px-3 py-2.5 " + s.bordure}>
                <p className={s.libelle + " flex items-center justify-between gap-2"}>
                  {l.libelle}
                  <Icone size={14} style={{ color: s.c(couleur) }} aria-label={l.defavorable ? "défavorable" : "favorable"} />
                </p>
                <p className="text-sm mt-0.5">
                  <span className={isDark ? "text-zinc-500" : "text-gray-400"}>{l.avant}</span>
                  <ArrowRight size={12} className={"inline mx-1 " + (isDark ? "text-zinc-600" : "text-gray-300")} />
                  <b style={{ color: s.c(couleur) }}>{l.apres}</b>
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Simulateur « Et si... ? » : le modèle recalcule le risque, rien n'est enregistré
function Simulateur({ analyse, isDark }) {
  const s = styles(isDark);
  const d = analyse.detail || {};
  const montantInitial = Math.round(analyse.montant || 0);
  const echeanceInitiale = Number(String(chiffre(d, "Échéance")).replace(/\D/g, "")) || 0;
  const dureeInitiale = Math.min(Math.max(echeanceInitiale ? Math.round(montantInitial / echeanceInitiale) : 24, 6), 120);
  const [montant, setMontant] = useState(montantInitial);
  const [duree, setDuree] = useState(dureeInitiale);
  const [resultat, setResultat] = useState(null);
  const [calcul, setCalcul] = useState(false);
  const [erreur, setErreur] = useState("");

  useEffect(() => {
    if (!montant) return undefined;
    let actif = true;
    const t = setTimeout(() => {
      setCalcul(true);
      simulerAnalyse(analyse.id, montant, duree)
        .then((r) => { if (actif) { setResultat(r); setErreur(""); } })
        .catch(() => { if (actif) setErreur("Simulation impossible pour le moment. Réessayez."); })
        .finally(() => { if (actif) setCalcul(false); });
    }, 250);
    return () => { actif = false; clearTimeout(t); };
  }, [analyse.id, montant, duree]);

  const modifie = montant !== montantInitial || duree !== dureeInitiale;
  const norme = d.norme_endettement || 0.33;
  const accorde = resultat?.decision === "ACCORDE";
  const curseur = "w-full accent-[#2E86C1]";

  return (
    <div className={s.carte + " p-5 mb-5"}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <p className={s.titre + " flex items-center gap-2"}><SlidersHorizontal size={16} style={{ color: s.c(BLEU) }} /> Simuler d'autres conditions</p>
          <p className={s.sous}>Le modèle recalcule le risque en direct. Rien n'est enregistré. Échéance estimée hors intérêts.</p>
        </div>
        {modifie && (
          <button onClick={() => { setMontant(montantInitial); setDuree(dureeInitiale); }} className={s.bouton}>
            <RotateCcw size={15} /> Revenir au dossier
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-5">
        <div className="space-y-6">
          <div>
            <div className="flex justify-between items-baseline mb-2">
              <label htmlFor="sim-montant" className={s.libelle}>Montant du crédit</label>
              <span className={s.valeur}>{fcfa(montant)}</span>
            </div>
            <input id="sim-montant" type="range" className={curseur} min={Math.round(montantInitial * 0.1 / 10000) * 10000 || 10000}
              max={Math.round(montantInitial * 1.5 / 10000) * 10000} step={10000} value={montant}
              onChange={(e) => setMontant(Number(e.target.value))} />
            <div className={"flex justify-between text-[11px] mt-1 " + (isDark ? "text-zinc-600" : "text-gray-400")}>
              <span>{fcfa(montantInitial * 0.1)}</span><span>Demandé : {fcfa(montantInitial)}</span><span>{fcfa(montantInitial * 1.5)}</span>
            </div>
          </div>
          <div>
            <div className="flex justify-between items-baseline mb-2">
              <label htmlFor="sim-duree" className={s.libelle}>Durée</label>
              <span className={s.valeur}>{duree} mois</span>
            </div>
            <input id="sim-duree" type="range" className={curseur} min={6} max={120} step={1} value={duree}
              onChange={(e) => setDuree(Number(e.target.value))} />
            <div className={"flex justify-between text-[11px] mt-1 " + (isDark ? "text-zinc-600" : "text-gray-400")}>
              <span>6 mois</span><span>Demandé : {dureeInitiale} mois</span><span>120 mois</span>
            </div>
          </div>
        </div>

        <div className={"rounded-xl p-4 " + s.fond}>
          {erreur ? <p className="text-sm" style={{ color: ROUGE }}>{erreur}</p> : !resultat ? (
            <div className="py-8 text-center"><Loader2 size={22} className={"animate-spin mx-auto " + (isDark ? "text-zinc-600" : "text-gray-300")} /></div>
          ) : (
            <>
              <div className="flex items-center justify-between gap-3">
                <p className="flex items-center gap-2 text-lg font-bold" style={{ color: s.c(accorde ? VERT : ROUGE) }}>
                  {accorde ? <CheckCircle2 size={20} /> : <XCircle size={20} />}
                  {modifie ? (accorde ? "Serait accordé" : "Serait refusé") : (accorde ? "Accordé (dossier actuel)" : "Refusé (dossier actuel)")}
                </p>
                {calcul && <Loader2 size={16} className={"animate-spin " + (isDark ? "text-zinc-500" : "text-gray-400")} />}
              </div>
              <EchelleRisque proba={resultat.probabilite_defaut} isDark={isDark} />
              <div className="grid grid-cols-2 gap-4">
                <div><p className={s.libelle}>Échéance mensuelle</p><p className={s.valeur}>{fcfa(resultat.echeance)}</p></div>
                <div>
                  <p className={s.libelle}>Taux d'endettement</p>
                  <p className="text-sm font-semibold" style={{ color: s.c(resultat.endettement > norme ? ROUGE : VERT) }}>
                    {resultat.endettement != null ? pct(resultat.endettement) : "—"}
                    <span className={"font-normal text-xs ml-1 " + (isDark ? "text-zinc-500" : "text-gray-400")}>norme {pct(norme)}</span>
                  </p>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Pistes trouvées par le modèle (dossier refusé) */}
      {resultat && !accorde && (
        <div className={"mt-5 pt-4 border-t " + s.bordure}>
          {resultat.pistes.length > 0 ? (
            <>
              <p className={s.titre + " mb-2"}>Conditions qui seraient acceptées</p>
              <div className="flex flex-wrap gap-2">
                {resultat.pistes.map((p) => (
                  <button key={p.type} onClick={() => { setMontant(Math.round(p.montant)); setDuree(p.duree_mois); }}
                    className="text-left rounded-xl border px-4 py-2.5 transition hover:opacity-90"
                    style={{ borderColor: VERT + "66", background: VERT + (isDark ? "1f" : "0d") }}>
                    <p className="text-sm font-medium" style={{ color: s.c(VERT) }}>
                      {p.type === "montant" ? `Réduire à ${fcfa(p.montant)} sur ${p.duree_mois} mois` : `Étaler sur ${p.duree_mois} mois pour ${fcfa(p.montant)}`}
                    </p>
                    <p className={s.libelle}>Risque {pct(p.probabilite_defaut)}, échéance {fcfa(p.echeance)}. Cliquez pour l'appliquer.</p>
                  </button>
                ))}
              </div>
            </>
          ) : (
            <p className={s.texte}>
              Ni une baisse du montant (jusqu'à 30 % de la demande) ni un allongement de la durée (jusqu'à 120 mois) ne
              suffisent à passer sous le seuil de 70 % : le refus tient surtout au profil du client, en particulier ses
              notes de solvabilité. Voir les recommandations ci-dessous.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// Facteurs déterminants organisés : équilibre du dossier, puis ce qui pèse
// contre et ce qui joue en faveur, avec la part de chaque facteur
function FacteursOrganises({ facteurs, accorde, isDark }) {
  const s = styles(isDark);
  const total = facteurs.reduce((t, f) => t + Math.abs(f.contribution), 0) || 1;
  const part = (f) => Math.abs(f.contribution) / total;
  const contre = facteurs.filter((f) => f.contribution > 0).sort((x, y) => part(y) - part(x));
  const pour = facteurs.filter((f) => f.contribution <= 0).sort((x, y) => part(y) - part(x));
  const partContre = contre.reduce((t, f) => t + part(f), 0);
  return (
    <>
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className={s.titre}>Facteurs déterminants</p>
          <p className={s.sous}>Les éléments du dossier qui ont le plus compté dans la décision, et leur part d'influence</p>
        </div>
      </div>

      {/* Équilibre du dossier */}
      <div className="mt-4 mb-5">
        <div className="flex justify-between text-xs mb-1.5">
          <span className="font-medium" style={{ color: s.c(ROUGE) }}>Contre le dossier : {pct(partContre)}</span>
          <span className="font-medium" style={{ color: s.c(VERT) }}>En faveur : {pct(1 - partContre)}</span>
        </div>
        <div className="flex h-3 rounded-full overflow-hidden gap-0.5">
          <div style={{ width: partContre * 100 + "%", background: ROUGE }} />
          <div style={{ width: (1 - partContre) * 100 + "%", background: VERT }} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ColonneFacteurs part={part} isDark={isDark} titre="Pèsent contre le dossier" liste={contre} couleur={ROUGE} Icone={TrendingUp} vide="Aucun facteur défavorable marquant." />
        <ColonneFacteurs part={part} isDark={isDark} titre="Jouent en faveur du dossier" liste={pour} couleur={VERT} Icone={TrendingDown} vide="Aucun facteur favorable marquant." />
      </div>
      <p className={s.libelle + " mt-4"}>
        {accorde ? "Les facteurs défavorables restent des points de vigilance pour le suivi du crédit."
          : "Agir sur les facteurs défavorables est la meilleure piste pour une nouvelle demande."}
      </p>
    </>
  );
}

function Lignes({ lignes, isDark, colonnes = 1 }) {
  const s = styles(isDark);
  return (
    <div className={colonnes === 2 ? "grid grid-cols-1 sm:grid-cols-2 gap-x-8" : ""}>
      {lignes.map(([l, v]) => (
        <div key={l} className={"flex items-baseline justify-between gap-3 py-2 border-b " + s.bordure}>
          <span className={s.libelle}>{l}</span><span className={s.valeur + " text-right"}>{v}</span>
        </div>
      ))}
    </div>
  );
}

function Conseils({ d, accorde, isDark, colonnes }) {
  const s = styles(isDark);
  if (!d.conseils) return null;
  return (
    <ul className={colonnes === 2 ? "grid grid-cols-1 lg:grid-cols-2 gap-x-8 gap-y-2" : "space-y-2"}>
      {d.conseils.lignes.map((l) => (
        <li key={l} className={"flex gap-2.5 " + s.texte}>
          <span className="mt-2 w-1.5 h-1.5 rounded-full shrink-0" style={{ background: accorde ? VERT : BLEU }} />{l}
        </li>
      ))}
    </ul>
  );
}

function chiffre(d, libelle) {
  const ligne = [...(d.credit || []), ...(d.client || [])].find(([l]) => l === libelle);
  return ligne ? ligne[1] : "—";
}

function DetailAnalyse({ analyse, isDark, estAdmin, maintenant, onMaj, onSupprimer }) {
  const s = styles(isDark);
  const navigate = useNavigate();
  const d = analyse.detail || {};
  const accorde = analyse.decision === "ACCORDE";
  const couleur = accorde ? VERT : ROUGE;
  const historique = d.historique_client || [];
  const premiere = historique[0];
  const ecart = premiere ? Math.round((analyse.probabilite_defaut - premiere.probabilite_defaut) * 100) : 0;
  const rembourses = historique.filter((a) => a.resultat_reel === "rembourse").length;
  const initiales = (analyse.nom_client || "?").split(" ").map((m) => m[0]).slice(0, 2).join("");
  const Tendance = ecart > 5 ? TrendingUp : ecart < -5 ? TrendingDown : Minus;
  const couleurTendance = ecart > 5 ? ROUGE : ecart < -5 ? VERT : BLEU;
  // Parcours long : faire défiler jusqu'à l'analyse affichée
  const refParcours = useRef(null);
  useEffect(() => {
    const zone = refParcours.current;
    const carte = zone?.querySelector("[data-courant]");
    if (zone && carte) zone.scrollLeft = carte.offsetLeft - zone.offsetLeft - (zone.clientWidth - carte.clientWidth) / 2;
  }, [analyse.id]);
  return (
    <>
      {/* Identité du client */}
      <div className={s.carte + " p-5 mb-5"}>
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <Retour isDark={isDark} />
            <div className="w-12 h-12 rounded-xl grid place-items-center text-white font-semibold" style={{ background: BLEU }}>{initiales}</div>
            <div>
              <h1 className={"text-xl font-bold " + (isDark ? "text-white" : "text-gray-800")}>{analyse.nom_client}</h1>
              <p className={"text-sm " + (isDark ? "text-zinc-400" : "text-gray-500")}>
                {chiffre(d, "Âge")}, {chiffre(d, "Situation familiale").toLowerCase()}
              </p>
            </div>
          </div>
          <Actions analyse={analyse} isDark={isDark} estAdmin={estAdmin} onSupprimer={onSupprimer} />
        </div>
        <div className={"grid grid-cols-2 md:grid-cols-4 gap-4 mt-5 pt-4 border-t " + s.bordure}>
          <div><p className={s.libelle}>Client depuis</p><p className={s.valeur + " mt-0.5"}>{premiere ? moisAnnee(premiere.date) : "—"}</p></div>
          <div><p className={s.libelle}>Analyses</p><p className={s.valeur + " mt-0.5"}>{historique.length}</p></div>
          <div><p className={s.libelle}>Crédits remboursés</p><p className={s.valeur + " mt-0.5"}>{rembourses}</p></div>
          <div>
            <p className={s.libelle}>Évolution depuis la 1re analyse</p>
            <p className="flex items-center gap-1 text-sm font-semibold mt-0.5" style={{ color: s.c(couleurTendance) }}>
              <Tendance size={16} /> {ecart > 0 ? "+" : ""}{ecart} points
            </p>
          </div>
        </div>
      </div>

      <AlerteTendance historique={historique} idCourant={analyse.id} isDark={isDark} />

      {/* Parcours : une carte par analyse, de la plus ancienne à la plus récente */}
      <div className="flex items-baseline justify-between mb-3">
        <p className={s.titre}>Parcours du client</p>
        <p className={s.libelle}>Cliquez sur une analyse pour l'afficher</p>
      </div>
      <div ref={refParcours} className="flex items-stretch gap-2 overflow-x-auto pb-2 mb-5">
        {historique.map((a, i) => {
          const courant = a.id === analyse.id;
          return (
            <div key={a.id} data-courant={courant || undefined} className="flex items-stretch gap-2 flex-1 min-w-[190px]">
              <button onClick={() => !courant && navigate(`/analyse/${a.id}${window.location.search}`)}
                className={"flex-1 flex flex-col justify-start text-left rounded-xl border p-4 transition " + (courant ? "" : (isDark ? "bg-zinc-900 border-zinc-800 hover:border-zinc-600" : "bg-white border-gray-100 shadow-sm hover:border-gray-300"))}
                style={courant ? { borderColor: BLEU, boxShadow: `0 0 0 3px ${BLEU}33`, background: isDark ? "#0c1a24" : "#fff" } : {}}>
                <div className="flex justify-between items-baseline">
                  <span className={s.libelle}>{dateCourte(a.date)}</span>
                  {courant && <span className="text-[11px] font-medium" style={{ color: s.c(BLEU) }}>Affichée</span>}
                </div>
                <p className="text-2xl font-bold mt-1" style={{ color: s.c(teinte(a.probabilite_defaut)) }}>{pct(a.probabilite_defaut)}</p>
                <p className={s.libelle + " mb-2"}>{fcfa(a.montant)}</p>
                <div className="flex gap-1.5 flex-wrap items-center">
                  <Pastille couleur={a.decision === "ACCORDE" ? VERT : ROUGE} isDark={isDark}>{a.decision === "ACCORDE" ? "Accordé" : "Refusé"}</Pastille>
                  {a.decision === "ACCORDE" && <IssuePastille a={a} maintenant={maintenant} isDark={isDark} />}
                </div>
              </button>
              {i < historique.length - 1 && <span aria-hidden="true" className={"self-center " + (isDark ? "text-zinc-600" : "text-gray-300")}>→</span>}
            </div>
          );
        })}
      </div>

      <Changements changements={d.changements} probaActuelle={analyse.probabilite_defaut} isDark={isDark} />

      {/* Décision | dossier */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mb-5">
        <div className={s.carte + " p-5 lg:col-span-5"}>
          <p className={s.libelle}>Analyse n° {analyse.id}, le {dateLongue(analyse.date_analyse)} à {heure(analyse.date_analyse)}, par {analyse.nom_agent}</p>
          <div className="flex items-center justify-between gap-3 mt-2">
            <p className="flex items-center gap-2 text-2xl font-bold" style={{ color: s.c(couleur) }}>
              {accorde ? <CheckCircle2 size={24} /> : <XCircle size={24} />} Crédit {accorde ? "accordé" : "refusé"}
            </p>
            <Pastille couleur={teinte(analyse.probabilite_defaut)} isDark={isDark}>Risque {NIVEAU[analyse.classe_risque]}</Pastille>
          </div>
          <p className={s.libelle + " mt-4"}>Probabilité de défaut</p>
          <EchelleRisque proba={analyse.probabilite_defaut} isDark={isDark} />
          <p className={s.texte}>{d.motivation}</p>
        </div>
        <div className={s.carte + " p-5 lg:col-span-7"}>
          <p className={s.titre}>Le dossier</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 mt-1">
            <div>
              <p className={"text-[11px] font-medium mt-3 " + (isDark ? "text-zinc-400" : "text-gray-500")}>Crédit demandé</p>
              <Lignes isDark={isDark} lignes={d.credit || []} />
            </div>
            <div>
              <p className={"text-[11px] font-medium mt-3 " + (isDark ? "text-zinc-400" : "text-gray-500")}>Situation du demandeur</p>
              <Lignes isDark={isDark} lignes={(d.client || []).filter(([l]) => !["Âge", "Situation familiale"].includes(l))} />
            </div>
          </div>
          {d.endettement != null && (
            <div className="mt-5">
              <div className="flex items-baseline justify-between mb-1.5">
                <span className={s.libelle}>Taux d'endettement (échéance / revenu)</span>
                <span className="text-sm font-semibold" style={{ color: s.c(d.endettement > d.norme_endettement ? ROUGE : VERT) }}>
                  {pct(d.endettement)} <span className={"font-normal text-xs " + (isDark ? "text-zinc-500" : "text-gray-400")}>pour une norme de {pct(d.norme_endettement)}</span>
                </span>
              </div>
              <div className={"relative h-2 rounded-full " + (isDark ? "bg-zinc-800" : "bg-gray-100")}>
                <div className="h-2 rounded-full" style={{ width: Math.min(d.endettement, 1) * 100 + "%", background: d.endettement > d.norme_endettement ? ROUGE : VERT }} />
                <div className="absolute -top-1 h-4 w-0.5" style={{ left: d.norme_endettement * 100 + "%", background: isDark ? "#e4e4e7" : "#374151" }} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Facteurs déterminants */}
      <div className={s.carte + " p-5 mb-5"}>
        <FacteursOrganises facteurs={d.facteurs || []} accorde={accorde} isDark={isDark} />
      </div>

      <Simulateur key={analyse.id} analyse={analyse} isDark={isDark} />

      {/* Recommandations | issue */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className={s.carte + " p-5 lg:col-span-7"}>
          <p className={s.titre}>{d.conseils?.titre}</p>
          <p className={s.sous + " mb-3"}>{accorde ? "À respecter avant le déblocage des fonds" : "Pistes à proposer au client"}</p>
          <Conseils d={d} accorde={accorde} isDark={isDark} />
        </div>
        <div className="lg:col-span-5">
          <BlocIssue analyse={analyse} estAdmin={estAdmin} maintenant={maintenant} isDark={isDark} onMaj={onMaj} />
        </div>
      </div>
    </>
  );
}

export default function AnalyseDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isDark } = useTheme();
  const { utilisateur } = useAuth();
  const estAdmin = utilisateur?.role === "admin";
  // Analyse chargee, avec l'identifiant demande et l'heure du chargement
  const [etat, setEtat] = useState({ id: null, analyse: null, recu: 0 });
  const [suppression, setSuppression] = useState({ ouverte: false, enCours: false, erreur: "" });
  const analyse = etat.analyse;

  function charger() {
    return getAnalyse(id)
      .then((a) => setEtat({ id, analyse: a, recu: Date.now() }))
      .catch(() => setEtat({ id, analyse: null, recu: Date.now() }));
  }
  useEffect(() => { charger(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function supprimer() {
    setSuppression((s) => ({ ...s, enCours: true, erreur: "" }));
    try {
      await supprimerAnalyse(analyse.id);
      navigate("/historique", { replace: true, state: { message: `L'analyse n° ${analyse.id} de ${analyse.nom_client} a été supprimée.` } });
    } catch (e) {
      setSuppression({ ouverte: true, enCours: false, erreur: e?.response?.data?.detail || "Suppression impossible. Réessayez." });
    }
  }

  let contenu;
  if (etat.id !== id) {
    contenu = <div className="text-center py-20"><Loader2 size={30} className={"animate-spin mx-auto " + (isDark ? "text-zinc-600" : "text-gray-300")} /></div>;
  } else if (!analyse) {
    contenu = (
      <div className="text-center py-20">
        <p className={isDark ? "text-zinc-400" : "text-gray-500"}>Cette analyse n'existe pas ou a été supprimée.</p>
        <button onClick={() => navigate("/historique")} className="mt-4 px-4 py-2 rounded-lg text-white text-sm" style={{ backgroundColor: BLEU }}>
          Retour à l'historique
        </button>
      </div>
    );
  } else {
    contenu = (
      <>
        <DetailAnalyse analyse={analyse} isDark={isDark} estAdmin={estAdmin} maintenant={etat.recu} onMaj={charger}
          onSupprimer={() => setSuppression({ ouverte: true, enCours: false, erreur: "" })} />
        <ConfirmationSuppression
          ouverte={suppression.ouverte} enCours={suppression.enCours} erreur={suppression.erreur}
          titre={`Supprimer l'analyse n° ${analyse.id} ?`}
          details={[`Client : ${analyse.nom_client}`, `Date : ${dateLongue(analyse.date_analyse)}`,
            `Décision : ${analyse.decision === "ACCORDE" ? "accordé" : "refusé"} (${pct(analyse.probabilite_defaut)})`]}
          onConfirmer={supprimer} onAnnuler={() => setSuppression({ ouverte: false, enCours: false, erreur: "" })} />
      </>
    );
  }

  return (
    <div>
      <Header title="Détail de l'analyse" subtitle="Historique des analyses" />
      {contenu}
    </div>
  );
}

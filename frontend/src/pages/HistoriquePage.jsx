import { useState, useEffect, useMemo } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import Header from "../components/ui/Header";
import { getAnalyses, telechargerPdf, supprimerAnalyse } from "../services/analyseService";
import ConfirmationSuppression from "../components/ui/ConfirmationSuppression";
import { Loader2, Download, Search, Trash2, CheckCircle2, X } from "lucide-react";
import PiedDeListe from "../components/ui/PiedDeListe";
import useDefilementInfini from "../hooks/useDefilementInfini";

// Couleurs de l'application : chaque couleur garde un seul sens
const BLEU = "#2E86C1";
const VERT = "#0F6E56";
const ORANGE = "#d97706";
const ROUGE = "#c0392b";
const PAS = 20;   // lignes ajoutées à chaque chargement
const DELAI_SUIVI_JOURS = 30;

const LIBELLE_RISQUE = { faible: "Faible", moyen: "Moyen", eleve: "Élevé" };
const COULEUR_RISQUE = { faible: VERT, moyen: ORANGE, eleve: ROUGE };
const COULEUR_RISQUE_SOMBRE = { faible: "#34d399", moyen: "#fbbf24", eleve: "#f87171" };
const PERIODES = [
  { cle: "tout", libelle: "Toute la période", jours: null },
  { cle: "7j", libelle: "7 derniers jours", jours: 7 },
  { cle: "30j", libelle: "30 derniers jours", jours: 30 },
  { cle: "90j", libelle: "3 derniers mois", jours: 90 },
];

// Dates en heure du Tchad (l'API renvoie de l'UTC sans fuseau)
const versDate = (d) => new Date(String(d).endsWith("Z") ? d : d + "Z");
const formatDate = (d) => d ? versDate(d).toLocaleString("fr-FR", {
  day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Africa/Ndjamena",
}).replace(" ", " à ") : "—";
const fcfa = (n) => (n ? Number(n).toLocaleString("fr-FR", { maximumFractionDigits: 0 }) : "—");
const sansAccent = (t) => (t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

// Issue d'un crédit : remboursé, défaut, à renseigner (accordé depuis plus de 30 jours) ou en cours
function issueDe(a, maintenant) {
  if (a.decision !== "ACCORDE") return null;
  if (a.resultat_reel) return a.resultat_reel;
  const jours = (maintenant - versDate(a.date_analyse)) / 86400000;
  return jours > DELAI_SUIVI_JOURS ? "a_renseigner" : "en_cours";
}

function Pastille({ couleur, isDark, children }) {
  return (
    <span className="inline-flex items-center text-xs px-2 py-0.5 rounded-full border font-medium whitespace-nowrap"
      style={{ color: isDark ? undefined : couleur, borderColor: couleur + "55", backgroundColor: couleur + (isDark ? "26" : "0d") }}>
      {children}
    </span>
  );
}

function Filtre({ actif, onClick, children, isDark }) {
  return (
    <button onClick={onClick} aria-pressed={actif}
      className={"px-3 py-1.5 rounded-lg text-xs font-medium transition border " +
        (actif ? "text-white border-transparent"
          : (isDark ? "border-zinc-800 text-zinc-400 hover:bg-zinc-800" : "border-gray-200 text-gray-600 bg-white hover:bg-gray-50"))}
      style={actif ? { backgroundColor: BLEU } : {}}>
      {children}
    </button>
  );
}

export default function HistoriquePage() {
  const { isDark } = useTheme();
  const { utilisateur } = useAuth();
  const estAdmin = utilisateur?.role === "admin";
  const navigate = useNavigate();
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur] = useState("");
  const [decision, setDecision] = useState("toutes");
  // Filtre « Issue à renseigner » pré-sélectionné depuis une notification (?issue=a_renseigner)
  const [issue, setIssue] = useState(() => new URLSearchParams(window.location.search).get("issue") || "toutes");
  const [periode, setPeriode] = useState("tout");
  const [recherche, setRecherche] = useState("");
  const [pdfEnCours, setPdfEnCours] = useState(null);
  const [maintenant] = useState(() => Date.now());
  const location = useLocation();
  // Message après une suppression (depuis cette page ou depuis le détail)
  const [message, setMessage] = useState(location.state?.message || "");
  const [aSupprimer, setASupprimer] = useState(null);
  const [suppression, setSuppression] = useState({ enCours: false, erreur: "" });

  async function confirmerSuppression() {
    setSuppression({ enCours: true, erreur: "" });
    try {
      await supprimerAnalyse(aSupprimer.id);
      setAnalyses((liste) => liste.filter((a) => a.id !== aSupprimer.id));
      setMessage(`L'analyse n° ${aSupprimer.id} de ${aSupprimer.nom_client} a été supprimée.`);
      setASupprimer(null);
      setSuppression({ enCours: false, erreur: "" });
    } catch (e) {
      setSuppression({ enCours: false, erreur: e?.response?.data?.detail || "Suppression impossible. Réessayez." });
    }
  }

  useEffect(() => {
    getAnalyses()
      .then((a) => { setAnalyses(a); setErreur(""); })
      .catch(() => setErreur("Impossible de charger l'historique. Vérifiez la connexion, puis actualisez la page."))
      .finally(() => setLoading(false));
  }, []);

  // Filtres période + recherche (client ou agent), puis décision et issue
  const dansPeriode = useMemo(() => {
    const jours = PERIODES.find((p) => p.cle === periode)?.jours;
    const mot = sansAccent(recherche.trim());
    return analyses.filter((a) => {
      const okPeriode = !jours || (maintenant - versDate(a.date_analyse)) / 86400000 <= jours;
      const okRecherche = !mot || sansAccent(a.nom_client).includes(mot) || sansAccent(a.nom_agent).includes(mot);
      return okPeriode && okRecherche;
    });
  }, [analyses, periode, recherche, maintenant]);

  const compte = (dec) => dansPeriode.filter((a) => dec === "toutes" || a.decision === dec).length;
  const aRenseigner = dansPeriode.filter((a) => issueDe(a, maintenant) === "a_renseigner").length;
  const filtrees = dansPeriode.filter((a) =>
    (decision === "toutes" || a.decision === decision) &&
    (issue === "toutes" || issueDe(a, maintenant) === issue));

  const [nbAffiches, repere, chargementSuite, reinitialiser] = useDefilementInfini(filtrees.length, PAS);
  const visibles = filtrees.slice(0, nbAffiches);
  const changer = (setter) => (v) => { setter(v); reinitialiser(); };

  async function exporterPdf(e, id) {
    e.stopPropagation();
    setPdfEnCours(id);
    try {
      const blob = await telechargerPdf(id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `fiche_decision_${id}.pdf`; a.click();
      window.URL.revokeObjectURL(url);
    } catch { setErreur("Téléchargement de la fiche impossible. Réessayez."); }
    finally { setPdfEnCours(null); }
  }

  const carte = "rounded-2xl border overflow-hidden " +
    (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");
  const th = "py-2.5 text-[11px] font-medium " + (isDark ? "text-zinc-500" : "text-gray-400");
  const td = "py-3 text-xs " + (isDark ? "text-zinc-300" : "text-gray-600");
  const bordure = isDark ? "border-zinc-800" : "border-gray-100";
  const champ = "rounded-lg border outline-none focus:ring-2 focus:ring-[#2E86C1]/40 text-sm " +
    (isDark ? "bg-zinc-900 border-zinc-800 text-white" : "bg-white border-gray-200 text-gray-800");

  const libelleIssue = {
    rembourse: <Pastille couleur={VERT} isDark={isDark}>Remboursé</Pastille>,
    defaut: <Pastille couleur={ROUGE} isDark={isDark}>Défaut</Pastille>,
    a_renseigner: <Pastille couleur={ORANGE} isDark={isDark}>À renseigner</Pastille>,
    en_cours: <span className={isDark ? "text-zinc-500" : "text-gray-400"}>En cours</span>,
  };

  return (
    <div>
      <Header title="Historique des analyses" subtitle="Toutes les analyses réalisées, de la plus récente à la plus ancienne" />

      {/* Filtres */}
      <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <Filtre isDark={isDark} actif={decision === "toutes"} onClick={() => changer(setDecision)("toutes")}>Toutes ({compte("toutes")})</Filtre>
          <Filtre isDark={isDark} actif={decision === "ACCORDE"} onClick={() => changer(setDecision)("ACCORDE")}>Accordées ({compte("ACCORDE")})</Filtre>
          <Filtre isDark={isDark} actif={decision === "REFUSE"} onClick={() => changer(setDecision)("REFUSE")}>Refusées ({compte("REFUSE")})</Filtre>
          <span className={"w-px h-5 mx-1 " + (isDark ? "bg-zinc-800" : "bg-gray-200")} />
          <Filtre isDark={isDark} actif={issue === "a_renseigner"}
            onClick={() => changer(setIssue)(issue === "a_renseigner" ? "toutes" : "a_renseigner")}>
            Issue à renseigner ({aRenseigner})
          </Filtre>
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select value={periode} onChange={(e) => changer(setPeriode)(e.target.value)} aria-label="Période"
            className={champ + " px-3 py-2"}>
            {PERIODES.map((p) => <option key={p.cle} value={p.cle}>{p.libelle}</option>)}
          </select>
          <div className="relative flex-1 sm:w-64">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input value={recherche} onChange={(e) => changer(setRecherche)(e.target.value)}
              placeholder={estAdmin ? "Client ou agent" : "Rechercher un client"} aria-label="Rechercher"
              className={champ + " w-full pl-9 pr-3 py-2"} />
          </div>
        </div>
      </div>

      {message && (
        <div role="status" className="mb-4 flex items-center gap-2 rounded-xl border px-4 py-3 text-sm"
          style={{ borderColor: VERT + "55", color: isDark ? "#34d399" : VERT, backgroundColor: VERT + (isDark ? "1f" : "0d") }}>
          <CheckCircle2 size={16} /> <span className="flex-1">{message}</span>
          <button onClick={() => setMessage("")} aria-label="Fermer le message"><X size={15} /></button>
        </div>
      )}

      {erreur && (
        <div className="mb-4 rounded-xl border px-4 py-3 text-sm"
          style={{ borderColor: ROUGE + "55", color: ROUGE, backgroundColor: ROUGE + "0d" }}>{erreur}</div>
      )}

      <div className={carte}>
        {loading ? (
          <div className="text-center py-12"><Loader2 size={26} className={"animate-spin mx-auto " + (isDark ? "text-zinc-600" : "text-gray-300")} /></div>
        ) : filtrees.length === 0 ? (
          <div className="text-center py-12">
            <p className={"text-sm " + (isDark ? "text-zinc-400" : "text-gray-500")}>
              {analyses.length === 0 ? "Aucune analyse pour l'instant." : "Aucune analyse ne correspond à ces filtres."}
            </p>
            {analyses.length === 0 ? (
              <button onClick={() => navigate("/analyse")} className="mt-3 text-sm font-medium" style={{ color: BLEU }}>
                Lancer une première analyse
              </button>
            ) : (
              <button onClick={() => { setDecision("toutes"); setIssue("toutes"); setPeriode("tout"); setRecherche(""); reinitialiser(); }}
                className="mt-3 text-sm font-medium" style={{ color: BLEU }}>
                Effacer les filtres
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto px-4 lg:px-5">
              <table className="w-full min-w-[820px]">
                <thead><tr>
                  <th className={th + " text-left"}>Date</th>
                  <th className={th + " text-left"}>Client</th>
                  <th className={th + " text-right pr-6"}>Montant (FCFA)</th>
                  <th className={th + " text-left"}>Probabilité de défaut</th>
                  <th className={th + " text-left"}>Décision</th>
                  <th className={th + " text-left"}>Issue</th>
                  {estAdmin && <th className={th + " text-left"}>Agent</th>}
                  <th className={th}><span className="sr-only">Actions</span></th>
                </tr></thead>
                <tbody>
                  {visibles.map((a) => {
                    const couleur = COULEUR_RISQUE[a.classe_risque] || BLEU;
                    return (
                      <tr key={a.id} onClick={() => navigate(`/analyse/${a.id}`)}
                        className={"border-t cursor-pointer transition-colors " + bordure + " " +
                          (isDark ? "hover:bg-zinc-800/40" : "hover:bg-gray-50")}>
                        <td className={td + " whitespace-nowrap"}>{formatDate(a.date_analyse)}</td>
                        <td className={td + " font-medium " + (isDark ? "text-zinc-100" : "text-gray-800")}>{a.nom_client || "—"}</td>
                        <td className={td + " text-right pr-6 tabular-nums"}>{fcfa(a.montant)}</td>
                        <td className="py-3">
                          <span className="inline-flex items-center gap-2.5">
                            <span className="text-xs font-semibold w-9 text-right tabular-nums"
                              style={{ color: isDark ? COULEUR_RISQUE_SOMBRE[a.classe_risque] || couleur : couleur }}>
                              {Math.round(a.probabilite_defaut * 100)} %
                            </span>
                            <Pastille couleur={couleur} isDark={isDark}>{LIBELLE_RISQUE[a.classe_risque] || a.classe_risque}</Pastille>
                          </span>
                        </td>
                        <td className="py-3">
                          <Pastille couleur={a.decision === "ACCORDE" ? VERT : ROUGE} isDark={isDark}>
                            {a.decision === "ACCORDE" ? "Accordé" : "Refusé"}
                          </Pastille>
                        </td>
                        <td className="py-3 text-xs">{libelleIssue[issueDe(a, maintenant)] || <span className={isDark ? "text-zinc-600" : "text-gray-300"}>—</span>}</td>
                        {estAdmin && <td className={td + " whitespace-nowrap"}>{a.nom_agent || "—"}</td>}
                        <td className="py-3 text-right whitespace-nowrap">
                          {estAdmin && (
                            <button onClick={(e) => { e.stopPropagation(); setSuppression({ enCours: false, erreur: "" }); setASupprimer(a); }}
                              aria-label="Supprimer l'analyse" title="Supprimer l'analyse"
                              className={"inline-flex w-7 h-7 mr-1.5 items-center justify-center rounded-lg border transition " +
                                (isDark ? "border-zinc-700 text-zinc-400 hover:text-red-400 hover:border-red-900" : "border-gray-200 text-gray-500 hover:text-red-700 hover:border-red-200")}>
                              <Trash2 size={13} />
                            </button>
                          )}
                          <button onClick={(e) => exporterPdf(e, a.id)} aria-label="Télécharger la fiche PDF" title="Télécharger la fiche PDF"
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

            <PiedDeListe affiches={nbAffiches} total={filtrees.length} nom="analyses" feminin
              repere={repere} chargement={chargementSuite} isDark={isDark} />
          </>
        )}
      </div>
      <ConfirmationSuppression
        ouverte={!!aSupprimer} enCours={suppression.enCours} erreur={suppression.erreur}
        titre={aSupprimer ? `Supprimer l'analyse n° ${aSupprimer.id} ?` : ""}
        details={aSupprimer ? [`Client : ${aSupprimer.nom_client}`, `Date : ${formatDate(aSupprimer.date_analyse)}`,
          `Décision : ${aSupprimer.decision === "ACCORDE" ? "accordé" : "refusé"} (${Math.round(aSupprimer.probabilite_defaut * 100)} %)`] : []}
        onConfirmer={confirmerSuppression} onAnnuler={() => setASupprimer(null)} />
    </div>
  );
}

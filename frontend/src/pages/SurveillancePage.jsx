import { useState } from "react";
import { useTheme } from "../context/ThemeContext";
import Header from "../components/ui/Header";
import { analyserDerive } from "../services/driftService";
import {
  Activity, Play, Loader2, CheckCircle2, AlertTriangle, AlertCircle, Info,
} from "lucide-react";

// Libellés lisibles des variables
const LIBELLES = {
  AMT_INCOME_TOTAL: "Revenu", AMT_CREDIT: "Montant du crédit",
  AMT_ANNUITY: "Échéance", AGE_ANNEES: "Âge",
  ANCIENNETE_EMPLOI_ANNEES: "Ancienneté d'emploi",
  EXT_SOURCE_2: "Score de solvabilité 2", EXT_SOURCE_3: "Score de solvabilité 3",
};
function libelle(v) { return LIBELLES[v] || v; }

export default function SurveillancePage() {
  const { isDark } = useTheme();
  const [resultat, setResultat] = useState(null);
  const [loading, setLoading] = useState(false);

  async function lancer() {
    setLoading(true);
    setResultat(null);
    try { setResultat(await analyserDerive()); }
    catch { setResultat({ statut: "erreur" }); }
    finally { setLoading(false); }
  }

  const cardClass = "rounded-2xl border p-5 " +
    (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");

  // Couleur et icône selon le niveau de dérive d'une variable
  function styleNiveau(niveau) {
    if (niveau === "stable") return { couleur: "#0F6E56", label: "Stable" };
    if (niveau === "derive moderee") return { couleur: "#d97706", label: "Dérive modérée" };
    return { couleur: "#c0392b", label: "Dérive importante" };
  }

  return (
    <div>
      <Header title="Surveillance du modèle" subtitle="Détection de la dérive des données (data drift)" />

      {/* Explication pédagogique */}
      <div className={cardClass + " mb-5 flex items-start gap-3"}>
        <div className="h-9 w-9 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: "#2E86C11a" }}>
          <Info size={18} style={{ color: "#2E86C1" }} />
        </div>
        <div>
          <p className={"text-sm font-medium mb-1 " + (isDark ? "text-white" : "text-gray-800")}>
            Qu'est-ce que la dérive des données ?
          </p>
          <p className={"text-sm " + (isDark ? "text-zinc-400" : "text-gray-600")}>
            La dérive survient lorsque les caractéristiques des nouveaux dossiers s'éloignent
            de celles sur lesquelles le modèle a été entraîné. Le modèle devient alors moins fiable,
            et un réentraînement peut être nécessaire. On la mesure avec l'indice PSI.
          </p>
        </div>
      </div>

      {/* Bouton de lancement */}
      <div className="mb-5">
        <button onClick={lancer} disabled={loading}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white transition disabled:opacity-60"
          style={{ backgroundColor: "#2E86C1" }}>
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
          {loading ? "Analyse en cours..." : "Lancer l'analyse de dérive"}
        </button>
      </div>

      {/* Résultat */}
      {resultat && resultat.statut === "insuffisant" && (
        <div className={cardClass + " flex items-start gap-3"}>
          <AlertCircle size={20} className="text-amber-500 shrink-0 mt-0.5" />
          <div>
            <p className={"text-sm font-medium " + (isDark ? "text-white" : "text-gray-800")}>Données insuffisantes</p>
            <p className={"text-sm mt-0.5 " + (isDark ? "text-zinc-400" : "text-gray-600")}>{resultat.message}</p>
          </div>
        </div>
      )}

      {resultat && resultat.statut === "erreur" && (
        <div className={cardClass}>
          <p className="text-sm text-red-500">Une erreur est survenue lors de l'analyse.</p>
        </div>
      )}

      {resultat && resultat.statut === "ok" && (
        <div className="space-y-5">
          {/* Statut global */}
          <StatutGlobal resultat={resultat} isDark={isDark} cardClass={cardClass} />

          {/* Détail par variable */}
          <div className={cardClass}>
            <p className={"font-semibold text-sm mb-1 " + (isDark ? "text-white" : "text-gray-800")}>
              Dérive par variable
            </p>
            <p className={"text-xs mb-4 " + (isDark ? "text-zinc-500" : "text-gray-400")}>
              Indice PSI : &lt; 0,10 stable · 0,10 à 0,25 modérée · &gt; 0,25 importante
            </p>
            <div className="space-y-3">
              {Object.entries(resultat.derive_par_variable || {}).map(([variable, info]) => {
                const { couleur, label } = styleNiveau(info.niveau);
                const largeur = Math.min((info.psi / 0.3) * 100, 100);
                return (
                  <div key={variable}>
                    <div className="flex justify-between items-center mb-1">
                      <span className={"text-sm " + (isDark ? "text-zinc-300" : "text-gray-700")}>{libelle(variable)}</span>
                      <span className="text-xs font-medium" style={{ color: couleur }}>
                        PSI {info.psi} · {label}
                      </span>
                    </div>
                    <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: isDark ? "#27272a" : "#f3f4f6" }}>
                      <div className="h-full rounded-full transition-all duration-700"
                        style={{ width: largeur + "%", backgroundColor: couleur }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Bloc de statut global
function StatutGlobal({ resultat, isDark, cardClass }) {
  const deriveMax = resultat.derive_maximale;
  let config;
  if (deriveMax < 0.10) {
    config = { Icone: CheckCircle2, couleur: "#0F6E56", titre: "Modèle stable" };
  } else if (deriveMax < 0.25) {
    config = { Icone: AlertTriangle, couleur: "#d97706", titre: "Dérive modérée détectée" };
  } else {
    config = { Icone: AlertCircle, couleur: "#c0392b", titre: "Dérive importante détectée" };
  }
  const { Icone, couleur, titre } = config;

  return (
    <div className={cardClass}>
      <div className="flex items-center gap-4">
        <div className="h-14 w-14 rounded-xl flex items-center justify-center shrink-0" style={{ backgroundColor: couleur + "1a" }}>
          <Icone size={28} style={{ color: couleur }} />
        </div>
        <div className="flex-1">
          <p className="text-lg font-bold" style={{ color: couleur }}>{titre}</p>
          <p className={"text-sm mt-0.5 " + (isDark ? "text-zinc-400" : "text-gray-600")}>{resultat.recommandation}</p>
          <p className={"text-xs mt-1 " + (isDark ? "text-zinc-500" : "text-gray-400")}>
            Basé sur {resultat.nb_analyses} analyses · Dérive maximale : {resultat.derive_maximale}
          </p>
        </div>
      </div>
    </div>
  );
}
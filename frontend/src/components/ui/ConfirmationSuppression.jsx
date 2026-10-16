import { useEffect, useRef } from "react";
import { Trash2, Loader2, Lock } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";

const ROUGE = "#c0392b";
const ORANGE = "#d97706";

const AVERTISSEMENT = "La suppression est définitive : l'analyse disparaîtra de l'historique, du tableau de bord et de CrediBot.";

// Fenêtre de confirmation avant une suppression définitive.
// ouverte : affichée ou non ; details : lignes décrivant ce qui sera supprimé ;
// bloque : la suppression n'est pas possible (seul le message est affiché).
export default function ConfirmationSuppression({ ouverte, titre, details = [], enCours, erreur, onConfirmer, onAnnuler,
  avertissement = AVERTISSEMENT, bloque = false }) {
  const { isDark } = useTheme();
  const refAnnuler = useRef(null);

  useEffect(() => {
    if (!ouverte) return undefined;
    refAnnuler.current?.focus();
    const touche = (e) => { if (e.key === "Escape" && !enCours) onAnnuler(); };
    window.addEventListener("keydown", touche);
    return () => window.removeEventListener("keydown", touche);
  }, [ouverte, enCours, onAnnuler]);

  if (!ouverte) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="titre-suppression">
      <div className="absolute inset-0 bg-black/40" onClick={() => !enCours && onAnnuler()} />
      <div className={"relative w-full max-w-md rounded-2xl border p-6 shadow-xl " +
        (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100")}>
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl grid place-items-center shrink-0"
            style={{ background: (bloque ? ORANGE : ROUGE) + "1a", color: bloque ? ORANGE : ROUGE }}>
            {bloque ? <Lock size={18} /> : <Trash2 size={18} />}
          </div>
          <div>
            <h2 id="titre-suppression" className={"font-semibold " + (isDark ? "text-white" : "text-gray-800")}>{titre}</h2>
            {details.length > 0 && (
              <ul className={"text-sm mt-2 space-y-0.5 " + (isDark ? "text-zinc-300" : "text-gray-600")}>
                {details.map((d) => <li key={d}>{d}</li>)}
              </ul>
            )}
            <p className={"text-sm mt-3 " + (isDark ? "text-zinc-400" : "text-gray-500")}>
              {avertissement}
            </p>
            {erreur && <p className="text-sm mt-3" style={{ color: ROUGE }}>{erreur}</p>}
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <button ref={refAnnuler} onClick={onAnnuler} disabled={enCours}
            className={"px-4 py-2 rounded-lg text-sm font-medium border transition disabled:opacity-60 " +
              (isDark ? "border-zinc-700 text-zinc-300 hover:bg-zinc-800" : "border-gray-200 text-gray-700 hover:bg-gray-50")}>
            {bloque ? "Fermer" : "Annuler"}
          </button>
          {!bloque && <button onClick={onConfirmer} disabled={enCours}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-60"
            style={{ background: ROUGE }}>
            {enCours ? <Loader2 size={15} className="animate-spin" /> : <Trash2 size={15} />} Supprimer définitivement
          </button>}
        </div>
      </div>
    </div>
  );
}

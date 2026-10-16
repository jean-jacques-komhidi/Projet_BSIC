import { useState, useEffect } from "react";
import { seConnecter } from "../services/authService";
import { useTheme } from "../context/ThemeContext";
import { Eye, EyeOff, Sun, Moon, Mail, Lock, AlertCircle, ArrowBigUp, Loader2 } from "lucide-react";
import logoBsic from "../assets/logo_bsic_recadre.png";
import fond1 from "../assets/connexion/fond_1.jpg";
import fond2 from "../assets/connexion/fond_2.jpg";
import fond3 from "../assets/connexion/fond_3.jpg";
import fond4 from "../assets/connexion/fond_4.jpg";

// Photos du diaporama d'arriere-plan (remplacer un fichier suffit pour changer une photo)
const PHOTOS = [fond1, fond2, fond3, fond4];
const DUREE_PHOTO_MS = 6000;
const VERSION = "1.7";

// Diaporama plein ecran : les photos se succedent en fondu sous un voile bleu nuit.
// Si l'utilisateur a demande moins d'animations, la premiere photo reste fixe.
function Diaporama() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const moinsDanimations = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (moinsDanimations) return undefined;
    const minuterie = setInterval(() => setIndex((i) => (i + 1) % PHOTOS.length), DUREE_PHOTO_MS);
    return () => clearInterval(minuterie);
  }, []);

  return (
    <div className="fixed inset-0 overflow-hidden" aria-hidden="true">
      {PHOTOS.map((photo, i) => (
        <div
          key={photo}
          className="absolute bg-cover bg-center transition-opacity duration-[1600ms] ease-in-out motion-reduce:transition-none"
          style={{
            inset: "-12px",
            backgroundImage: `url(${photo})`,
            filter: "blur(2px) saturate(.85)",
            opacity: i === index ? 1 : 0,
          }}
        />
      ))}
      <div className="absolute inset-0"
        style={{ background: "linear-gradient(180deg, rgba(8,30,58,.80) 0%, rgba(8,30,58,.88) 100%)" }} />
    </div>
  );
}

function LoginPage({ onConnexionReussie }) {
  const { isDark, toggleTheme } = useTheme();
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [voirMdp, setVoirMdp] = useState(false);
  const [majuscules, setMajuscules] = useState(false);
  const [erreur, setErreur] = useState("");
  const [chargement, setChargement] = useState(false);

  async function gererConnexion(e) {
    e.preventDefault();
    setErreur("");
    setChargement(true);
    try {
      await seConnecter(email, motDePasse);
      onConnexionReussie();
    } catch (err) {
      if (err.response) {
        setErreur("E-mail ou mot de passe incorrect. Vérifiez vos identifiants, puis réessayez.");
      } else {
        // Pas de reponse du serveur (reseau, ou API en cours de demarrage sur l'hebergeur)
        setErreur("Le serveur ne répond pas. Réessayez dans un instant : le premier démarrage peut prendre une minute.");
      }
    } finally {
      setChargement(false);
    }
  }

  // Detecte la touche Verr. Maj pendant la saisie du mot de passe
  function verifierMajuscules(e) {
    if (e.getModifierState) setMajuscules(e.getModifierState("CapsLock"));
  }

  const inputClass = "w-full pl-10 pr-4 py-2.5 rounded-lg border outline-none text-sm transition " +
    "focus:border-[#2E86C1] focus:ring-2 focus:ring-[#2E86C1]/35 " +
    (isDark ? "bg-zinc-800 border-zinc-700 text-white placeholder-zinc-500" : "bg-white border-gray-200 text-gray-800 placeholder-gray-400");
  const labelClass = "block text-sm font-medium mb-1.5 " + (isDark ? "text-zinc-300" : "text-gray-700");
  const iconeClass = "absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none " + (isDark ? "text-zinc-500" : "text-gray-400");

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-8 relative overflow-hidden bg-[#0B2A4F]">
      <Diaporama />

      {/* Bouton thème en haut à droite */}
      <button onClick={toggleTheme} aria-label="Changer de thème"
        className={"absolute top-5 right-5 z-20 w-9 h-9 rounded-lg flex items-center justify-center border transition " +
          (isDark ? "border-zinc-800 text-zinc-400 hover:bg-zinc-800 bg-zinc-900" : "border-gray-200 text-gray-500 hover:bg-gray-50 bg-white")}>
        {isDark ? <Sun size={16} /> : <Moon size={16} />}
      </button>

      {/* Carte de connexion */}
      <div className={"w-full max-w-[420px] rounded-2xl overflow-hidden relative z-10 shadow-[0_24px_48px_-16px_rgba(0,0,0,0.5)] " +
        (isDark ? "bg-zinc-900" : "bg-white")}>
        <div className="px-8 pt-8 pb-6">
          {/* Logo et titre */}
          <div className="text-center mb-6">
            <img src={logoBsic} alt="BSIC Tchad"
              className={"h-14 mx-auto mb-3.5 " + (isDark ? "bg-white rounded-lg px-2 py-1 h-[68px]" : "")} />
            <h1 className={"text-2xl font-bold tracking-tight " + (isDark ? "text-white" : "text-gray-800")}>CREDISCORE</h1>
            <p className={"text-sm mt-1 " + (isDark ? "text-zinc-500" : "text-gray-400")}>BSIC Tchad - Scoring de crédit</p>
          </div>

          <p className={"text-[13.5px] leading-relaxed text-center mb-5 " + (isDark ? "text-zinc-400" : "text-gray-500")}>
            Connectez-vous avec les identifiants fournis par votre administrateur.
          </p>

          {/* Formulaire */}
          <form onSubmit={gererConnexion} className="space-y-4">
            {erreur && (
              <div role="alert" className={"flex items-start gap-2 rounded-lg border px-3 py-2.5 text-[13.5px] leading-snug " +
                (isDark ? "bg-red-500/10 border-red-900 text-red-400" : "bg-red-50 border-red-200 text-red-700")}>
                <AlertCircle size={16} className="shrink-0 mt-0.5" />
                <span>{erreur}</span>
              </div>
            )}

            <div>
              <label htmlFor="email" className={labelClass}>Adresse e-mail</label>
              <div className="relative">
                <Mail size={17} className={iconeClass} />
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="username"
                  className={inputClass}
                  placeholder="prenom.nom@bsic.td"
                />
              </div>
            </div>

            <div>
              <label htmlFor="mot-de-passe" className={labelClass}>Mot de passe</label>
              <div className="relative">
                <Lock size={17} className={iconeClass} />
                <input
                  id="mot-de-passe"
                  type={voirMdp ? "text" : "password"}
                  value={motDePasse}
                  onChange={(e) => setMotDePasse(e.target.value)}
                  onKeyUp={verifierMajuscules}
                  onKeyDown={verifierMajuscules}
                  onBlur={() => setMajuscules(false)}
                  required
                  autoComplete="current-password"
                  className={inputClass + " pr-10" + (erreur ? (isDark ? " border-red-900" : " border-red-300") : "")}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setVoirMdp(!voirMdp)}
                  aria-label={voirMdp ? "Masquer le mot de passe" : "Afficher le mot de passe"}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {voirMdp ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {majuscules && (
                <p className={"flex items-center gap-1.5 mt-1.5 text-[12.5px] " + (isDark ? "text-amber-500" : "text-amber-700")}>
                  <ArrowBigUp size={14} /> La touche Verr. Maj est activée.
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={chargement}
              className="w-full text-white py-2.5 rounded-lg font-medium transition disabled:opacity-75 hover:opacity-90 flex items-center justify-center gap-2"
              style={{ backgroundColor: "#2E86C1" }}
            >
              {chargement && <Loader2 size={16} className="animate-spin" />}
              {chargement ? "Connexion…" : "Se connecter"}
            </button>
          </form>

          <p className={"text-center text-[13px] mt-4 " + (isDark ? "text-zinc-400" : "text-gray-500")}>
            Mot de passe oublié ? Contactez votre administrateur.
          </p>
        </div>

        {/* Pied de carte */}
        <div className={"flex items-center justify-between gap-3 px-8 py-3 border-t text-xs " +
          (isDark ? "bg-zinc-950/40 border-zinc-800 text-zinc-500" : "bg-gray-50 border-gray-100 text-gray-400")}>
          <span className="flex items-center gap-1.5"><Lock size={12} /> Accès réservé au personnel habilité</span>
          <span>Version {VERSION}</span>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;

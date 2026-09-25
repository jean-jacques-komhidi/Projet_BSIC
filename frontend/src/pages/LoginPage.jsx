import { useState } from "react";
import { seConnecter } from "../services/authService";
import { useTheme } from "../context/ThemeContext";
import { Eye, EyeOff, Sun, Moon } from "lucide-react";
import logoBsic from "../assets/logo_bsic.png";

function LoginPage({ onConnexionReussie }) {
  const { isDark, toggleTheme } = useTheme();
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [voirMdp, setVoirMdp] = useState(false);
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
      setErreur("E-mail ou mot de passe incorrect.");
    } finally {
      setChargement(false);
    }
  }

  const inputClass = "w-full px-4 py-2.5 rounded-lg border outline-none focus:ring-2 focus:ring-blue-500 text-sm transition " +
    (isDark ? "bg-zinc-800 border-zinc-700 text-white placeholder-zinc-500" : "bg-white border-gray-200 text-gray-800 placeholder-gray-400");
  const labelClass = "block text-sm font-medium mb-1.5 " + (isDark ? "text-zinc-300" : "text-gray-700");

  return (
    <div className={"min-h-screen flex items-center justify-center px-4 relative overflow-hidden " +
      (isDark ? "bg-zinc-950" : "bg-gray-100")}>

      {/* Bouton thème en haut à droite */}
      <button onClick={toggleTheme}
        className={"absolute top-5 right-5 z-20 w-9 h-9 rounded-lg flex items-center justify-center border transition " +
          (isDark ? "border-zinc-800 text-zinc-400 hover:bg-zinc-800 bg-zinc-900" : "border-gray-200 text-gray-500 hover:bg-gray-50 bg-white")}>
        {isDark ? <Sun size={16} /> : <Moon size={16} />}
      </button>

      {/* Arrière-plan animé : formes floutées BSIC */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="blob blob-1" />
        <div className="blob blob-2" />
        <div className="blob blob-3" />
      </div>

      {/* Carte de connexion */}
      <div className={"w-full max-w-md rounded-2xl shadow-xl p-8 relative z-10 border backdrop-blur-xl " +
        (isDark ? "bg-zinc-900/90 border-zinc-800" : "bg-white/90 border-white/50")}>
        {/* Logo et titre */}
        <div className="text-center mb-8">
          <img src={logoBsic} alt="BSIC" className="h-20 mx-auto mb-4" />
          <h1 className={"text-2xl font-bold " + (isDark ? "text-white" : "text-gray-800")}>CREDISCORE</h1>
          <p className={"text-sm mt-1 " + (isDark ? "text-zinc-500" : "text-gray-400")}>BSIC Tchad - Scoring de crédit</p>
        </div>

        {/* Formulaire */}
        <form onSubmit={gererConnexion} className="space-y-4">
          <div>
            <label className={labelClass}>Adresse e-mail</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className={inputClass}
              placeholder="agent@bsic.td"
            />
          </div>

          <div>
            <label className={labelClass}>Mot de passe</label>
            <div className="relative">
              <input
                type={voirMdp ? "text" : "password"}
                value={motDePasse}
                onChange={(e) => setMotDePasse(e.target.value)}
                required
                className={inputClass + " pr-10"}
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setVoirMdp(!voirMdp)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {voirMdp ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {erreur && (
            <div className="rounded-lg px-3 py-2 text-sm text-center"
              style={{ backgroundColor: "#c0392b15", color: "#c0392b" }}>
              {erreur}
            </div>
          )}

          <button
            type="submit"
            disabled={chargement}
            className="w-full text-white py-2.5 rounded-lg font-medium transition disabled:opacity-60 hover:opacity-90"
            style={{ backgroundColor: "#2E86C1" }}
          >
            {chargement ? "Connexion..." : "Se connecter"}
          </button>
        </form>

        <p className={"text-center text-xs mt-6 " + (isDark ? "text-zinc-600" : "text-gray-400")}>
          Système de scoring crédit - BSIC Tchad
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
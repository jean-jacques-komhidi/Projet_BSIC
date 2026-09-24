import { useState } from "react";
import { seConnecter } from "../services/authService";
import { Eye, EyeOff } from "lucide-react";
import logoBsic from "../assets/logo_bsic.png";

function LoginPage({ onConnexionReussie }) {
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

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden bg-gris-clair">
      {/* Arrière-plan animé : formes floutées aux couleurs BSIC */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="blob blob-1" />
        <div className="blob blob-2" />
        <div className="blob blob-3" />
      </div>

      {/* Carte de connexion (au-dessus du fond) */}
      <div className="w-full max-w-md bg-white/90 backdrop-blur-xl rounded-2xl shadow-xl p-8 relative z-10 border border-white/50">
        {/* Logo et titre */}
        <div className="text-center mb-8">
          <img src={logoBsic} alt="BSIC" className="h-20 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-encre">CREDISCORE</h1>
          <p className="text-gris text-sm mt-1">BSIC Tchad - Scoring de crédit</p>
        </div>

        {/* Formulaire */}
        <form onSubmit={gererConnexion} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-encre mb-1">
              Adresse e-mail
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-bsic"
              placeholder="agent@bsic.td"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-encre mb-1">
              Mot de passe
            </label>
            <div className="relative">
              <input
                type={voirMdp ? "text" : "password"}
                value={motDePasse}
                onChange={(e) => setMotDePasse(e.target.value)}
                required
                className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-bsic"
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
            <p className="text-danger text-sm text-center">{erreur}</p>
          )}

          <button
            type="submit"
            disabled={chargement}
            className="w-full bg-bsic text-white py-2.5 rounded-lg font-medium hover:bg-bsic-dark transition disabled:opacity-60"
          >
            {chargement ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;
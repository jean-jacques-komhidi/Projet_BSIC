import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import Header from "../components/ui/Header";
import {
  getUtilisateurs, creerUtilisateur, modifierUtilisateur,
} from "../services/userService";
import { ArrowLeft, Save, Loader2, User, Mail, Lock, Shield } from "lucide-react";

export default function UtilisateurFormPage() {
  const { id } = useParams(); // présent si modification
  const navigate = useNavigate();
  const { isDark } = useTheme();
  const estModification = !!id;

  const [form, setForm] = useState({
    nom: "", email: "", mot_de_passe: "", role: "agent",
  });
  const [erreur, setErreur] = useState("");
  const [chargement, setChargement] = useState(false);
  const [chargementInitial, setChargementInitial] = useState(estModification);

  // En modification, charger l'utilisateur
  useEffect(() => {
    if (estModification) {
      getUtilisateurs()
        .then((liste) => {
          const u = liste.find((x) => String(x.id) === String(id));
          if (u) {
            setForm({ nom: u.nom, email: u.email, mot_de_passe: "", role: u.role });
          }
        })
        .catch(() => {})
        .finally(() => setChargementInitial(false));
    }
  }, [id]);

  function maj(champ, valeur) { setForm((f) => ({ ...f, [champ]: valeur })); }

  async function sauvegarder(e) {
    e.preventDefault();
    setErreur("");
    setChargement(true);
    try {
      if (estModification) {
        const donnees = { nom: form.nom, email: form.email, role: form.role };
        if (form.mot_de_passe.trim()) donnees.mot_de_passe = form.mot_de_passe;
        await modifierUtilisateur(id, donnees);
      } else {
        await creerUtilisateur(form);
      }
      navigate("/utilisateurs");
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setErreur(typeof detail === "string" ? detail : "Enregistrement impossible.");
    } finally {
      setChargement(false);
    }
  }

  const cardClass = "rounded-2xl border p-6 " +
    (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");
  const inputClass = "w-full pl-10 pr-3 py-2.5 rounded-lg border outline-none focus:ring-2 focus:ring-blue-500 text-sm " +
    (isDark ? "bg-zinc-800 border-zinc-700 text-white" : "bg-white border-gray-200 text-gray-800");
  const labelClass = "block text-sm font-medium mb-1.5 " + (isDark ? "text-zinc-300" : "text-gray-700");

  if (chargementInitial) {
    return <div className="text-center py-20"><Loader2 size={28} className="animate-spin mx-auto text-gray-300" /></div>;
  }

  return (
    <div>
      <Header
        title={estModification ? "Modifier l'utilisateur" : "Nouvel utilisateur"}
        subtitle="Gestion des comptes de l'application"
      />

      {/* Bouton retour */}
      <button onClick={() => navigate("/utilisateurs")}
        className={"flex items-center gap-2 mb-5 px-3 py-2 rounded-lg border text-sm transition " +
          (isDark ? "border-zinc-800 text-zinc-400 hover:bg-zinc-800" : "border-gray-200 text-gray-500 hover:bg-gray-50")}>
        <ArrowLeft size={16} /> Retour à la liste
      </button>

      {/* Formulaire */}
      <div className="max-w-lg mx-auto">
        <div className={cardClass}>
          <form onSubmit={sauvegarder} className="space-y-4">
            <div>
              <label className={labelClass}>Nom complet</label>
              <div className="relative">
                <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input value={form.nom} onChange={(e) => maj("nom", e.target.value)} required className={inputClass}
                  placeholder="Nom de l'utilisateur" />
              </div>
            </div>

            <div>
              <label className={labelClass}>Adresse e-mail</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input type="email" value={form.email} onChange={(e) => maj("email", e.target.value)} required className={inputClass}
                  placeholder="utilisateur@bsic.td" />
              </div>
            </div>

            <div>
              <label className={labelClass}>
                Mot de passe
                {estModification && <span className="text-xs font-normal text-gray-400 ml-1">(laisser vide pour ne pas changer)</span>}
              </label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input type="password" value={form.mot_de_passe} onChange={(e) => maj("mot_de_passe", e.target.value)}
                  required={!estModification} minLength={6} className={inputClass} placeholder="••••••••" />
              </div>
            </div>

            <div>
              <label className={labelClass}>Rôle</label>
              <div className="relative">
                <Shield size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <select value={form.role} onChange={(e) => maj("role", e.target.value)}
                  className={inputClass + " appearance-none"}>
                  <option value="agent">Agent de crédit</option>
                  <option value="admin">Administrateur</option>
                </select>
              </div>
            </div>

            {erreur && <p className="text-sm text-center text-red-500">{erreur}</p>}

            <div className="flex gap-3 pt-2">
              <button type="button" onClick={() => navigate("/utilisateurs")}
                className={"flex-1 py-2.5 rounded-lg text-sm font-medium border " +
                  (isDark ? "border-zinc-700 text-zinc-300" : "border-gray-200 text-gray-600")}>
                Annuler
              </button>
              <button type="submit" disabled={chargement}
                className="flex-1 py-2.5 rounded-lg text-sm font-medium text-white disabled:opacity-60 flex items-center justify-center gap-2"
                style={{ backgroundColor: "#2E86C1" }}>
                {chargement ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                {estModification ? "Enregistrer" : "Créer l'utilisateur"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
import { useState, useEffect } from "react";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import Header from "../components/ui/Header";
import { modifierMonProfil, getMesStatistiques, changerMotDePasse } from "../services/authService";
import { getMlflowRuns } from "../services/monitoringService";
import {
  User, Mail, Shield, Save, Edit2, CheckCircle, TrendingUp, Target,
  Lock, FileSearch, ThumbsUp, ThumbsDown, Calendar, KeyRound,
} from "lucide-react";

export default function ProfilPage() {
  const { isDark } = useTheme();
  const { utilisateur, rafraichir } = useAuth();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ nom: utilisateur?.nom || "", email: utilisateur?.email || "" });
  const [saved, setSaved] = useState("");
  const [erreur, setErreur] = useState("");
  const [modele, setModele] = useState(null);
  const [stats, setStats] = useState(null);

  // Section mot de passe
  const [ancienMdp, setAncienMdp] = useState("");
  const [nouveauMdp, setNouveauMdp] = useState("");
  const [erreurMdp, setErreurMdp] = useState("");

  useEffect(() => {
    getMlflowRuns().then((runs) => { if (runs && runs[0]) setModele(runs[0]); }).catch(() => {});
    getMesStatistiques().then(setStats).catch(() => {});
  }, []);
  useEffect(() => {
    setForm({ nom: utilisateur?.nom || "", email: utilisateur?.email || "" });
  }, [utilisateur]);

  async function sauvegarderInfos() {
    setErreur("");
    try {
      await modifierMonProfil({ nom: form.nom, email: form.email });
      await rafraichir();
      setEditing(false);
      setSaved("Informations mises à jour !");
      setTimeout(() => setSaved(""), 2500);
    } catch (err) {
      const d = err?.response?.data?.detail;
      setErreur(typeof d === "string" ? d : "Modification impossible.");
    }
  }

  async function changerMdp() {
    setErreurMdp("");
    if (!ancienMdp || !nouveauMdp) { setErreurMdp("Remplissez les deux champs."); return; }
    try {
      await changerMotDePasse(ancienMdp, nouveauMdp);
      setAncienMdp(""); setNouveauMdp("");
      setSaved("Mot de passe modifié !");
      setTimeout(() => setSaved(""), 2500);
    } catch (err) {
      const d = err?.response?.data?.detail;
      setErreurMdp(typeof d === "string" ? d : "Changement impossible.");
    }
  }

  const initiales = (utilisateur?.nom || "?").split(" ").map((m) => m[0]).slice(0, 2).join("").toUpperCase();
  const estAdmin = utilisateur?.role === "admin";

  const inputClass = "w-full border rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400 " +
    (isDark ? "bg-zinc-800 border-zinc-700 text-white placeholder-zinc-500" : "bg-gray-50 border-gray-200 text-gray-800");
  const labelClass = "text-xs font-medium uppercase tracking-wide mb-1.5 flex items-center gap-1.5 " +
    (isDark ? "text-zinc-500" : "text-gray-400");
  const cardClass = "rounded-2xl border " + (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");
  const affichage = "text-sm font-medium px-3.5 py-2.5 rounded-xl " + (isDark ? "bg-zinc-800 text-white" : "bg-gray-50 text-gray-800");

  const InfoModele = ({ Icone, label, valeur, vert }) => (
    <div className="flex items-center gap-3">
      <div className={"w-8 h-8 rounded-lg flex items-center justify-center shrink-0 " + (isDark ? "bg-zinc-800" : "bg-gray-100")}>
        <Icone size={14} className={isDark ? "text-zinc-400" : "text-gray-500"} />
      </div>
      <div>
        <p className={"text-xs " + (isDark ? "text-zinc-500" : "text-gray-400")}>{label}</p>
        <p className={"text-sm font-semibold " + (vert ? (isDark ? "text-emerald-400" : "text-emerald-600") : (isDark ? "text-white" : "text-gray-800"))}>{valeur}</p>
      </div>
    </div>
  );

  return (
    <div>
      <Header title="Mon profil" subtitle="Gérez vos informations personnelles" />

      <div className="max-w-4xl">
        {saved && (
          <div className={"mb-5 flex items-center gap-2 border rounded-xl px-4 py-3 text-xs " +
            (isDark ? "bg-emerald-500/10 border-emerald-900 text-emerald-400" : "bg-emerald-50 border-emerald-200 text-emerald-700")}>
            <CheckCircle size={14} /> {saved}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Colonne gauche */}
          <div className="space-y-5">
            {/* Avatar */}
            <div className={cardClass + " p-5 flex flex-col items-center text-center"}>
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-3 text-white text-xl font-bold" style={{ backgroundColor: "#2E86C1" }}>
                {initiales}
              </div>
              <p className={"font-semibold text-base " + (isDark ? "text-white" : "text-gray-800")}>{utilisateur?.nom}</p>
              <span className={"inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full border font-medium mt-2 " +
                (estAdmin ? (isDark ? "border-blue-800 text-blue-400" : "border-blue-200 text-blue-700") : (isDark ? "border-zinc-700 text-zinc-400" : "border-gray-200 text-gray-500"))}>
                <Shield size={11} /> {estAdmin ? "Administrateur" : "Agent de crédit"}
              </span>
              {stats?.membre_depuis && (
                <p className={"flex items-center gap-1 text-xs mt-2 " + (isDark ? "text-zinc-500" : "text-gray-400")}>
                  <Calendar size={11} /> Membre depuis le {stats.membre_depuis}
                </p>
              )}
            </div>

            {/* Statistiques d'activité */}
            <div className={cardClass + " p-5"}>
              <p className={"text-xs font-medium uppercase tracking-wider mb-4 " + (isDark ? "text-zinc-600" : "text-gray-400")}>Mon activité</p>
              <div className="space-y-3">
                <InfoModele Icone={FileSearch} label="Analyses réalisées" valeur={stats?.analyses_realisees ?? "—"} />
                <InfoModele Icone={ThumbsUp} label="Crédits accordés" valeur={stats?.credits_accordes ?? "—"} vert />
                <InfoModele Icone={ThumbsDown} label="Crédits refusés" valeur={stats?.credits_refuses ?? "—"} />
              </div>
            </div>

            {/* Modèle actif */}
            <div className={cardClass + " p-5"}>
              <p className={"text-xs font-medium uppercase tracking-wider mb-4 " + (isDark ? "text-zinc-600" : "text-gray-400")}>Modèle actif</p>
              <div className="space-y-3">
                <InfoModele Icone={TrendingUp} label="Algorithme" valeur={modele?.modele || "Gradient Boosting"} />
                <InfoModele Icone={Target} label="AUC-ROC" valeur={modele?.auc_roc || "0.753"} />
                <InfoModele Icone={CheckCircle} label="Statut" valeur="Opérationnel" vert />
              </div>
            </div>
          </div>

          {/* Colonne droite */}
          <div className="lg:col-span-2 space-y-5">
            {/* Informations personnelles */}
            <div className={cardClass + " p-5"}>
              <div className="flex items-center justify-between mb-5">
                <h2 className={"font-semibold text-sm " + (isDark ? "text-white" : "text-gray-800")}>Informations personnelles</h2>
                {!editing && (
                  <button onClick={() => setEditing(true)}
                    className={"flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border transition " +
                      (isDark ? "border-zinc-700 text-zinc-300 hover:bg-zinc-800" : "border-gray-200 text-gray-600 hover:bg-gray-50")}>
                    <Edit2 size={12} /> Modifier
                  </button>
                )}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}><User size={10} /> Nom complet</label>
                  {editing
                    ? <input value={form.nom} onChange={(e) => setForm({ ...form, nom: e.target.value })} className={inputClass} />
                    : <p className={affichage}>{utilisateur?.nom}</p>}
                </div>
                <div>
                  <label className={labelClass}><Shield size={10} /> Rôle</label>
                  <p className={affichage}>{estAdmin ? "Administrateur" : "Agent de crédit"}</p>
                </div>
                <div className="sm:col-span-2">
                  <label className={labelClass}><Mail size={10} /> Adresse e-mail</label>
                  {editing
                    ? <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className={inputClass} />
                    : <p className={affichage}>{utilisateur?.email}</p>}
                </div>
              </div>
              {erreur && <p className="text-sm text-red-500 mt-3">{erreur}</p>}
              {editing && (
                <div className="flex gap-3 mt-5">
                  <button onClick={() => { setEditing(false); setForm({ nom: utilisateur?.nom, email: utilisateur?.email }); setErreur(""); }}
                    className={"flex-1 py-2.5 rounded-xl text-sm font-medium border transition " +
                      (isDark ? "border-zinc-700 text-zinc-400 hover:bg-zinc-800" : "border-gray-200 text-gray-600 hover:bg-gray-50")}>
                    Annuler
                  </button>
                  <button onClick={sauvegarderInfos}
                    className="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white transition flex items-center justify-center gap-2" style={{ backgroundColor: "#2E86C1" }}>
                    <Save size={14} /> Sauvegarder
                  </button>
                </div>
              )}
            </div>

            {/* Section Sécurité */}
            <div className={cardClass + " p-5"}>
              <div className="flex items-center gap-2 mb-5">
                <KeyRound size={16} className={isDark ? "text-zinc-400" : "text-gray-500"} />
                <h2 className={"font-semibold text-sm " + (isDark ? "text-white" : "text-gray-800")}>Sécurité — Changer le mot de passe</h2>
              </div>
              <div className="space-y-4">
                <div>
                  <label className={labelClass}><Lock size={10} /> Mot de passe actuel</label>
                  <input type="password" value={ancienMdp} onChange={(e) => setAncienMdp(e.target.value)} className={inputClass} placeholder="••••••••" />
                </div>
                <div>
                  <label className={labelClass}><Lock size={10} /> Nouveau mot de passe</label>
                  <input type="password" value={nouveauMdp} onChange={(e) => setNouveauMdp(e.target.value)} minLength={6} className={inputClass} placeholder="Au moins 6 caractères" />
                </div>
                {erreurMdp && <p className="text-sm text-red-500">{erreurMdp}</p>}
                <button onClick={changerMdp}
                  className="w-full py-2.5 rounded-xl text-sm font-semibold text-white transition flex items-center justify-center gap-2" style={{ backgroundColor: "#2E86C1" }}>
                  <KeyRound size={14} /> Changer le mot de passe
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
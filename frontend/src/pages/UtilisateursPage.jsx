import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import Header from "../components/ui/Header";
import { getUtilisateurs, supprimerUtilisateur } from "../services/userService";
import { UserCog, Plus, Pencil, Trash2, Loader2, Shield, User } from "lucide-react";

export default function UtilisateursPage() {
  const { isDark } = useTheme();
  const { utilisateur: moi } = useAuth();
  const navigate = useNavigate();
  const [utilisateurs, setUtilisateurs] = useState([]);
  const [loading, setLoading] = useState(true);

  async function charger() {
    setLoading(true);
    try { setUtilisateurs(await getUtilisateurs()); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }
  useEffect(() => { charger(); }, []);

  async function supprimer(u) {
    if (u.id === moi.id) { alert("Vous ne pouvez pas vous supprimer vous-même."); return; }
    if (!confirm(`Supprimer l'utilisateur ${u.nom} ?`)) return;
    try { await supprimerUtilisateur(u.id); charger(); }
    catch { alert("Suppression impossible."); }
  }

  const cardClass = "rounded-2xl border overflow-hidden " +
    (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");
  const headClass = "text-xs uppercase tracking-wider " + (isDark ? "text-zinc-600" : "text-gray-400");
  const cellClass = "py-3 text-sm " + (isDark ? "text-zinc-300" : "text-gray-600");
  const borderB = isDark ? "border-zinc-800" : "border-gray-100";

  function badgeRole(role) {
    const admin = role === "admin";
    return (
      <span className={"inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium " +
        (admin
          ? (isDark ? "text-blue-400 border-blue-800" : "text-blue-700 border-blue-200")
          : (isDark ? "text-zinc-400 border-zinc-700" : "text-gray-500 border-gray-200"))}>
        {admin ? <Shield size={11} /> : <User size={11} />}
        {admin ? "Administrateur" : "Agent"}
      </span>
    );
  }

  const initiales = (nom) => (nom || "?").split(" ").map((m) => m[0]).slice(0, 2).join("").toUpperCase();

  return (
    <div>
      <Header title="Utilisateurs" subtitle="Gestion des comptes de l'application" />

      <div className="flex items-center justify-between gap-3 mb-5">
        <p className={"text-sm " + (isDark ? "text-zinc-400" : "text-gray-500")}>
          {utilisateurs.length} utilisateur{utilisateurs.length > 1 ? "s" : ""}
        </p>
        <button onClick={() => navigate("/utilisateurs/nouveau")}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium text-white transition hover:opacity-90"
          style={{ backgroundColor: "#2E86C1" }}>
          <Plus size={16} /> Nouvel utilisateur
        </button>
      </div>

      <div className={cardClass}>
        <div className={"flex items-center gap-3 p-4 lg:p-5 border-b " + borderB}>
          <UserCog size={16} className={isDark ? "text-zinc-500" : "text-gray-400"} />
          <h2 className={"font-semibold text-sm " + (isDark ? "text-white" : "text-gray-800")}>Liste des utilisateurs</h2>
        </div>

        {loading ? (
          <div className="text-center py-12"><Loader2 size={26} className={"animate-spin mx-auto " + (isDark ? "text-zinc-600" : "text-gray-300")} /></div>
        ) : utilisateurs.length === 0 ? (
          <p className={"text-center py-12 text-sm " + (isDark ? "text-zinc-500" : "text-gray-400")}>Aucun utilisateur.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-140">
              <thead>
                <tr className={"border-b " + borderB}>
                  <th className={"text-left py-3 px-4 lg:px-5 " + headClass}>Utilisateur</th>
                  <th className={"text-left py-3 " + headClass}>E-mail</th>
                  <th className={"text-center py-3 " + headClass}>Rôle</th>
                  <th className={"text-right py-3 pr-4 lg:pr-5 " + headClass}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {utilisateurs.map((u) => (
                  <tr key={u.id} className={"border-t transition-colors " +
                    (isDark ? "border-zinc-800/50 hover:bg-zinc-800/30" : "border-gray-50 hover:bg-gray-50/80")}>
                    <td className="py-3 px-4 lg:px-5">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-lg flex items-center justify-center text-white text-xs font-semibold shrink-0"
                          style={{ backgroundColor: "#2E86C1" }}>
                          {initiales(u.nom)}
                        </div>
                        <span className={"font-medium text-sm " + (isDark ? "text-white" : "text-gray-800")}>
                          {u.nom}{u.id === moi.id && <span className={"text-xs ml-2 " + (isDark ? "text-zinc-500" : "text-gray-400")}>(vous)</span>}
                        </span>
                      </div>
                    </td>
                    <td className={cellClass}>{u.email}</td>
                    <td className="py-3 text-center">{badgeRole(u.role)}</td>
                    <td className="py-3 text-right pr-4 lg:pr-5">
                      <div className="flex items-center justify-end gap-2">
                        <button onClick={() => navigate(`/utilisateurs/${u.id}/modifier`)}
                          className={"p-1.5 rounded-lg transition " + (isDark ? "hover:bg-zinc-800 text-zinc-400" : "hover:bg-gray-100 text-gray-500")}>
                          <Pencil size={15} />
                        </button>
                        {u.id !== moi.id && (
                          <button onClick={() => supprimer(u)}
                            className="p-1.5 rounded-lg transition hover:bg-red-50 text-red-500">
                            <Trash2 size={15} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
import { useState, useEffect } from "react";
import { useTheme } from "../context/ThemeContext";
import Header from "../components/ui/Header";
import { useNotifications } from "../context/NotificationsContext";
import {
  getNotifications, marquerLue, toutMarquerLu,
} from "../services/notificationService";
import {
  Bell, CheckCircle2, AlertTriangle, Info, CheckCheck, Loader2,
} from "lucide-react";

export default function NotificationsPage() {
  const { isDark } = useTheme();
  const { rafraichirCompteur } = useNotifications();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  async function charger() {
    setLoading(true);
    try { setNotifications(await getNotifications()); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }
  useEffect(() => { charger(); }, []);

  async function marquer(id) {
    try {
      await marquerLue(id);
      setNotifications((n) => n.map((x) => x.id === id ? { ...x, lue: true } : x));
      rafraichirCompteur();
    } catch {}
  }

  async function toutLire() {
    try {
      await toutMarquerLu();
      setNotifications((n) => n.map((x) => ({ ...x, lue: true })));
      rafraichirCompteur();
    } catch {}
  }

  // Icône et couleur selon le type
  function styleType(type) {
    switch (type) {
      case "succes": return { Icone: CheckCircle2, couleur: "#0F6E56" };
      case "alerte": return { Icone: AlertTriangle, couleur: "#d97706" };
      default: return { Icone: Info, couleur: "#2E86C1" };
    }
  }

  const formatDate = (d) => d
    ? new Date(d).toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" })
    : "";

  const nbNonLues = notifications.filter((n) => !n.lue).length;

  const cardClass = "rounded-2xl border overflow-hidden " +
    (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");
  const borderB = isDark ? "border-zinc-800" : "border-gray-100";

  return (
    <div>
      <Header title="Notifications" subtitle="Les événements de l'application" />

      {/* Barre d'actions */}
      <div className="flex items-center justify-between mb-5">
        <p className={"text-sm " + (isDark ? "text-zinc-400" : "text-gray-500")}>
          {nbNonLues > 0
            ? `${nbNonLues} notification${nbNonLues > 1 ? "s" : ""} non lue${nbNonLues > 1 ? "s" : ""}`
            : "Toutes les notifications sont lues"}
        </p>
        {nbNonLues > 0 && (
          <button onClick={toutLire}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium border transition hover:opacity-80"
            style={{ borderColor: "var(--bordure)", color: "var(--texte)" }}>
            <CheckCheck size={15} /> Tout marquer comme lu
          </button>
        )}
      </div>

      {/* Liste */}
      <div className={cardClass}>
        {loading ? (
          <div className="text-center py-16"><Loader2 size={26} className={"animate-spin mx-auto " + (isDark ? "text-zinc-600" : "text-gray-300")} /></div>
        ) : notifications.length === 0 ? (
          <div className="text-center py-16">
            <Bell size={36} className={"mx-auto mb-3 " + (isDark ? "text-zinc-700" : "text-gray-200")} />
            <p className={"text-sm " + (isDark ? "text-zinc-500" : "text-gray-400")}>Aucune notification pour l'instant.</p>
          </div>
        ) : (
          <div>
            {notifications.map((n) => {
              const { Icone, couleur } = styleType(n.type);
              return (
                <div key={n.id}
                  onClick={() => !n.lue && marquer(n.id)}
                  className={"flex items-start gap-3 p-4 lg:p-5 border-b transition cursor-pointer " + borderB + " " +
                    (n.lue ? "" : (isDark ? "bg-zinc-800/40" : "bg-blue-50/40")) +
                    (isDark ? " hover:bg-zinc-800/60" : " hover:bg-gray-50")}>
                  {/* Icône */}
                  <div className="h-9 w-9 rounded-lg flex items-center justify-center shrink-0"
                    style={{ backgroundColor: couleur + "1a" }}>
                    <Icone size={18} style={{ color: couleur }} />
                  </div>
                  {/* Contenu */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className={"font-medium text-sm " + (isDark ? "text-white" : "text-gray-800")}>{n.titre}</p>
                      {!n.lue && <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: "#2E86C1" }} />}
                    </div>
                    <p className={"text-sm mt-0.5 " + (isDark ? "text-zinc-400" : "text-gray-600")}>{n.message}</p>
                    <p className={"text-xs mt-1 " + (isDark ? "text-zinc-600" : "text-gray-400")}>{formatDate(n.date_creation)}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
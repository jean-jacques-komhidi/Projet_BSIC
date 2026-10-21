import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext";
import { useAuth } from "../../context/AuthContext";
import { useNotifications } from "../../context/NotificationsContext";
import { getNotifications, marquerLue, toutMarquerLu } from "../../services/notificationService";
import RechercheGlobale from "./RechercheGlobale";
import {
  Plus, Bell, ChevronLeft, ChevronRight, UserCircle, LogOut, AlertTriangle, AlertOctagon,
  Info, CheckCircle2, Loader2,
} from "lucide-react";

const BLEU = "#2E86C1";
const TYPES = {
  danger: [AlertOctagon, "#c0392b"],
  alerte: [AlertTriangle, "#b45309"],
  succes: [CheckCircle2, "#0F6E56"],
  info: [Info, BLEU],
};

// Ferme un menu déroulant quand on clique en dehors
function useClicExterieur(ouvert, fermer) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ouvert) return undefined;
    function clic(e) { if (ref.current && !ref.current.contains(e.target)) fermer(); }
    function echap(e) { if (e.key === "Escape") fermer(); }
    document.addEventListener("mousedown", clic);
    document.addEventListener("keydown", echap);
    return () => { document.removeEventListener("mousedown", clic); document.removeEventListener("keydown", echap); };
  }, [ouvert, fermer]);
  return ref;
}

function quand(date) {
  const d = new Date(date);
  const minutes = Math.round((Date.now() - d.getTime()) / 60000);
  if (minutes < 60) return minutes <= 1 ? "À l'instant" : `Il y a ${minutes} min`;
  if (minutes < 60 * 24) return `Il y a ${Math.round(minutes / 60)} h`;
  if (minutes < 60 * 48) return "Hier";
  return d.toLocaleDateString("fr-FR", { timeZone: "Africa/Ndjamena" });
}

function MenuNotifications({ c, isDark }) {
  const navigate = useNavigate();
  const { unreadCount, rafraichirCompteur } = useNotifications();
  const [ouvert, setOuvert] = useState(false);
  const [liste, setListe] = useState(null);
  const ref = useClicExterieur(ouvert, () => setOuvert(false));

  async function ouvrir() {
    const suivant = !ouvert;
    setOuvert(suivant);
    if (suivant) {
      setListe(null);
      try { setListe((await getNotifications()).slice(0, 3)); } catch { setListe([]); }
    }
  }

  async function choisir(n) {
    setOuvert(false);
    if (!n.lue) { try { await marquerLue(n.id); rafraichirCompteur(); } catch { /* sans effet */ } }
    navigate(n.lien || "/notifications");
  }

  async function toutLire() {
    try { await toutMarquerLu(); rafraichirCompteur(); setListe((l) => (l || []).map((n) => ({ ...n, lue: true }))); } catch { /* sans effet */ }
  }

  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={ouvrir} aria-label="Notifications"
        className={"relative w-10 h-10 rounded-xl flex items-center justify-center transition " + c.bouton + (ouvert ? " " + c.boutonActif : "")}>
        <Bell size={19} />
        {unreadCount > 0 && (
          <span className={"absolute top-1 right-1 min-w-4 h-4 px-1 rounded-full text-[10px] font-bold text-white flex items-center justify-center border-2 " + (isDark ? "border-zinc-950" : "border-white")}
            style={{ background: "#c0392b" }}>{unreadCount > 9 ? "9+" : unreadCount}</span>
        )}
      </button>
      {ouvert && (
        <div className={"absolute right-0 top-12 w-96 rounded-2xl border shadow-xl overflow-hidden z-50 " + c.panneau}>
          <div className="flex items-center justify-between px-4 pt-3.5 pb-2.5">
            <p className={"text-sm font-semibold " + c.fort}>Notifications</p>
            {unreadCount > 0 && <button type="button" onClick={toutLire} className="text-xs font-medium" style={{ color: BLEU }}>Tout marquer comme lu</button>}
          </div>
          {liste === null ? (
            <div className="py-8 flex justify-center"><Loader2 size={18} className={"animate-spin " + c.gris} /></div>
          ) : liste.length === 0 ? (
            <p className={"px-4 py-8 text-sm text-center border-t " + c.trait + " " + c.texte}>Aucune notification pour l'instant.</p>
          ) : liste.map((n) => {
            const [Icone, couleur] = TYPES[n.type] || TYPES.info;
            return (
              <button key={n.id} type="button" onClick={() => choisir(n)}
                className={"w-full flex gap-3 px-4 py-3 text-left border-t transition " + c.trait + " " + c.survol + (n.lue ? "" : isDark ? " bg-sky-950/20" : " bg-sky-50/50")}>
                <span className="w-8 h-8 rounded-full flex items-center justify-center shrink-0" style={{ color: couleur, background: couleur + (isDark ? "30" : "14") }}>
                  <Icone size={16} />
                </span>
                <span className="flex-1 min-w-0">
                  <span className={"block text-sm font-semibold " + c.fort}>{n.titre}</span>
                  <span className={"text-xs leading-relaxed mt-0.5 line-clamp-2 " + c.texte}>{n.message}</span>
                  <span className={"block text-[11px] mt-1 " + c.gris}>{quand(n.date_creation)}{n.texte_lien ? ` · ${n.texte_lien} ›` : ""}</span>
                </span>
                {!n.lue && <span className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ background: BLEU }} />}
              </button>
            );
          })}
          <Link to="/notifications" onClick={() => setOuvert(false)}
            className={"block text-center text-sm font-medium py-2.5 border-t " + c.trait + " " + c.survol} style={{ color: BLEU }}>
            Voir toutes les notifications
          </Link>
        </div>
      )}
    </div>
  );
}

function MenuUtilisateur({ c, isDark }) {
  const navigate = useNavigate();
  const { utilisateur, deconnexion } = useAuth();
  const { unreadCount } = useNotifications();
  const { mode, setMode } = useTheme();
  const [ouvert, setOuvert] = useState(false);
  const ref = useClicExterieur(ouvert, () => setOuvert(false));
  const initiales = (utilisateur?.nom || "?").split(" ").map((m) => m[0]).slice(0, 2).join("").toUpperCase();
  const role = utilisateur?.role === "admin" ? "Administrateur" : "Agent de crédit";
  const aller = (chemin) => { setOuvert(false); navigate(chemin); };

  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={() => setOuvert((o) => !o)} aria-label="Menu du compte" title={`${utilisateur?.nom} · ${role}`}
        className={"w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-semibold transition " + (ouvert ? (isDark ? "ring-2 ring-sky-800" : "ring-2 ring-sky-200") : "")}
        style={{ background: BLEU }}>
        {initiales}
      </button>
      {ouvert && (
        <div className={"absolute right-0 top-12 w-72 rounded-2xl border shadow-xl overflow-hidden z-50 " + c.panneau}>
          <div className={"flex items-center gap-3 px-4 py-4 border-b " + c.trait}>
            <span className="w-11 h-11 rounded-full flex items-center justify-center text-white font-semibold shrink-0" style={{ background: BLEU }}>{initiales}</span>
            <span className="min-w-0">
              <span className={"block text-sm font-semibold truncate " + c.fort}>{utilisateur?.nom}</span>
              <span className={"block text-xs truncate " + c.texte}>{utilisateur?.email}</span>
              <span className={"block text-[11px] " + c.gris}>{role}</span>
            </span>
          </div>
          <button type="button" onClick={() => aller("/profil")} className={"w-full flex items-center gap-3 px-4 py-2.5 text-sm " + c.fort + " " + c.survol}>
            <UserCircle size={17} className={c.gris} /> Mon profil
          </button>
          <button type="button" onClick={() => aller("/notifications")} className={"w-full flex items-center gap-3 px-4 py-2.5 text-sm " + c.fort + " " + c.survol}>
            <Bell size={17} className={c.gris} /> Notifications
            {unreadCount > 0 && <span className={"ml-auto text-xs " + c.gris}>{unreadCount} non lue{unreadCount > 1 ? "s" : ""}</span>}
          </button>
          <p className={"text-[11px] uppercase tracking-wider px-4 pt-2.5 pb-1.5 " + c.gris}>Thème</p>
          <div className={"flex mx-4 mb-3 rounded-lg border overflow-hidden text-xs " + c.trait}>
            {[["clair", "Clair"], ["sombre", "Sombre"], ["systeme", "Système"]].map(([cle, libelle]) => (
              <button key={cle} type="button" onClick={() => setMode(cle)}
                className={"flex-1 py-1.5 transition " + (mode === cle ? "font-semibold" : c.texte)}
                style={mode === cle ? { background: isDark ? "#1e3a5f" : "#e8f0fe", color: isDark ? "#93c5fd" : "#1a56b0" } : {}}>
                {libelle}
              </button>
            ))}
          </div>
          <button type="button" onClick={() => { setOuvert(false); deconnexion(); navigate("/login"); }}
            className={"w-full flex items-center gap-3 px-4 py-3 text-sm border-t " + c.trait + " " + c.survol} style={{ color: "#c0392b" }}>
            <LogOut size={17} /> Se déconnecter
          </button>
        </div>
      )}
    </div>
  );
}

// fil : chemin de la page, ex. [{ libelle: "Historique", vers: "/historique" }, { libelle: "CRED-2026-0121" }]
export default function Header({ title, subtitle, fil }) {
  const { isDark } = useTheme();
  const navigate = useNavigate();
  const c = {
    panneau: isDark ? "bg-zinc-900 border-zinc-700" : "bg-white border-gray-200",
    fort: isDark ? "text-zinc-100" : "text-gray-800",
    texte: isDark ? "text-zinc-400" : "text-gray-500",
    gris: isDark ? "text-zinc-500" : "text-gray-400",
    trait: isDark ? "border-zinc-800" : "border-gray-100",
    survol: isDark ? "hover:bg-zinc-800/70" : "hover:bg-gray-50",
    bouton: isDark ? "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200" : "text-gray-500 hover:bg-gray-100 hover:text-gray-700",
    boutonActif: isDark ? "bg-zinc-800 text-zinc-200" : "bg-gray-100 text-gray-700",
  };
  const retour = fil?.find((f) => f.vers);

  return (
    <header className={"hidden lg:flex fixed top-0 left-64 right-0 z-30 h-[72px] px-8 items-center gap-6 border-b transition-colors duration-300 " +
      (isDark ? "bg-zinc-950 border-zinc-800" : "bg-white border-gray-100")}>
      <div className="min-w-0 w-64 xl:w-72 shrink-0">
        {fil?.length ? (
          <nav className={"flex items-center gap-1 text-xs mb-0.5 " + c.gris} aria-label="Fil d'Ariane">
            {retour && (
              <button type="button" onClick={() => navigate(retour.vers)} aria-label="Retour" className={"-ml-1 rounded " + c.bouton}><ChevronLeft size={14} /></button>
            )}
            {fil.map((f, i) => (
              <span key={f.libelle} className="flex items-center gap-1 min-w-0">
                {i > 0 && <ChevronRight size={12} />}
                {f.vers ? <Link to={f.vers} className={"font-medium hover:underline " + c.texte}>{f.libelle}</Link> : <span className="truncate">{f.libelle}</span>}
              </span>
            ))}
          </nav>
        ) : null}
        <h1 className={"text-base font-semibold truncate " + c.fort}>{title}</h1>
        {subtitle && <p className={"text-xs mt-0.5 truncate " + c.gris}>{subtitle}</p>}
      </div>

      <RechercheGlobale />

      <div className="flex items-center gap-2 shrink-0">
        <Link to="/analyse" className="hidden xl:flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl text-sm font-semibold text-white transition hover:opacity-90"
          style={{ background: BLEU }}>
          <Plus size={16} /> Nouvelle analyse
        </Link>
        <Link to="/analyse" aria-label="Nouvelle analyse" className="xl:hidden w-10 h-10 rounded-xl flex items-center justify-center text-white" style={{ background: BLEU }}>
          <Plus size={18} />
        </Link>
        <MenuNotifications c={c} isDark={isDark} />
        <MenuUtilisateur c={c} isDark={isDark} />
      </div>
    </header>
  );
}

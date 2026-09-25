import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext";
import { useNotifications } from "../../context/NotificationsContext";
import { useAuth } from "../../context/AuthContext";
import {
  LayoutDashboard, FileSearch, Users, Bell, History,
  MessageSquare, UserCog, Activity, UserCircle,
  Moon, Sun, LogOut, Menu, X,
} from "lucide-react";
import logoBsic from "../../assets/logo_bsic.png";

const BLEU = "#2E86C1";

export default function Sidebar() {
  const { isDark, toggleTheme } = useTheme();
  const { unreadCount } = useNotifications();
  const { utilisateur, deconnexion } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const initiales = utilisateur?.nom
    ? utilisateur.nom.split(" ").map((m) => m[0]).slice(0, 2).join("").toUpperCase()
    : "?";
  const estAdmin = utilisateur?.role === "admin";

  const sectionLabel = "text-[10px] font-semibold uppercase tracking-[0.12em] px-3 mb-2 mt-5 " +
    (isDark ? "text-zinc-600" : "text-gray-400");

  const sidebarClass = "flex flex-col " + (isDark ? "bg-zinc-950" : "bg-white");

  const Logo = () => (
    <div className={"flex items-center gap-3 px-5 py-5 border-b " +
      (isDark ? "border-zinc-800/80" : "border-gray-100")}>
      <img src={logoBsic} alt="BSIC" className="w-9 h-9 shrink-0" />
      <div>
        <p className={"font-bold text-sm tracking-tight " + (isDark ? "text-white" : "text-gray-800")}>CREDISCORE</p>
        <p className={"text-xs " + (isDark ? "text-zinc-500" : "text-gray-400")}>BSIC Tchad</p>
      </div>
    </div>
  );

  const Lien = ({ to, icone: Icone, children, onClose, badge }) => (
    <NavLink
      to={to}
      end={to === "/tableau-de-bord"}
      onClick={onClose}
      className="relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200"
    >
      {({ isActive }) => (
        <span className="flex items-center gap-3 w-full rounded-lg px-1"
          style={{ color: isActive ? BLEU : (isDark ? "#a1a1aa" : "#6b7280") }}>
          <Icone size={17} style={{ color: isActive ? BLEU : "currentColor" }} />
          <span className="flex-1">{children}</span>
          {badge > 0 && (
            <span className="text-xs px-1.5 py-0.5 rounded-full font-semibold text-white" style={{ backgroundColor: BLEU }}>
              {badge}
            </span>
          )}
        </span>
      )}
    </NavLink>
  );

  const NavLinks = ({ onClose }) => (
    <div className="[&_a:hover]:bg-gray-50 dark:[&_a:hover]:bg-zinc-800/50 dark:[&_a.active]:bg-zinc-800/40">
      <p className={sectionLabel}>Principal</p>
      <Lien to="/tableau-de-bord" icone={LayoutDashboard} onClose={onClose}>Tableau de bord</Lien>
      <Lien to="/analyse" icone={FileSearch} onClose={onClose}>Analyse de crédit</Lien>
      <Lien to="/clients" icone={Users} onClose={onClose}>Clients</Lien>
      <Lien to="/historique" icone={History} onClose={onClose}>Historique</Lien>
      <Lien to="/notifications" icone={Bell} onClose={onClose} badge={unreadCount}>Notifications</Lien>

      <p className={sectionLabel}>Assistant</p>
      <Lien to="/assistant" icone={MessageSquare} onClose={onClose}>Assistant IA</Lien>

      {estAdmin && (
        <>
          <p className={sectionLabel}>Administration</p>
          <Lien to="/utilisateurs" icone={UserCog} onClose={onClose}>Utilisateurs</Lien>
          <Lien to="/monitoring" icone={Activity} onClose={onClose}>Monitoring</Lien>
        </>
      )}

      <p className={sectionLabel}>Compte</p>
      <Lien to="/profil" icone={UserCircle} onClose={onClose}>Mon profil</Lien>
      <button
        onClick={() => { toggleTheme(); onClose && onClose(); }}
        className={"flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 w-full text-left " +
          (isDark ? "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200" : "text-gray-500 hover:bg-gray-50 hover:text-gray-800")}
      >
        {isDark ? <Sun size={17} /> : <Moon size={17} />}
        Mode {isDark ? "clair" : "sombre"}
      </button>
    </div>
  );

  const Footer = ({ onClose }) => (
    <div className={"border-t px-3 py-3 space-y-2 " + (isDark ? "border-zinc-800/80" : "border-gray-100")}>
      <div className={"flex items-center gap-3 px-3 py-2.5 rounded-xl " + (isDark ? "bg-zinc-900" : "bg-gray-50")}>
        <div className="w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold shrink-0 text-white"
          style={{ backgroundColor: BLEU }}>
          {initiales}
        </div>
        <div className="min-w-0">
          <p className={"text-xs font-semibold truncate " + (isDark ? "text-zinc-100" : "text-gray-800")}>{utilisateur?.nom}</p>
          <p className={"text-xs truncate " + (isDark ? "text-zinc-500" : "text-gray-400")}>
            {estAdmin ? "Administrateur" : "Agent de crédit"}
          </p>
        </div>
      </div>
      <button
        onClick={() => { deconnexion(); onClose && onClose(); }}
        className={"flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 w-full text-left " +
          (isDark ? "text-red-400 hover:bg-red-950/30" : "text-red-600 hover:bg-red-50")}
      >
        <LogOut size={17} />
        Déconnexion
      </button>
    </div>
  );

  return (
    <>
      {/* DESKTOP */}
      <aside
        className={"hidden lg:flex fixed left-0 top-0 h-full w-64 z-40 flex-col " + sidebarClass}
        style={{
          boxShadow: isDark
            ? "1px 0 0 rgba(255,255,255,0.04), 4px 0 24px rgba(0,0,0,0.4)"
            : "1px 0 0 rgba(0,0,0,0.04), 4px 0 24px rgba(0,0,0,0.04)",
        }}
      >
        <Logo />
        <nav className="flex-1 px-3 py-2 space-y-0.5 overflow-y-auto">
          <NavLinks onClose={null} />
        </nav>
        <Footer onClose={null} />
      </aside>

      {/* MOBILE header */}
      <div className={"lg:hidden fixed top-0 left-0 right-0 z-40 flex items-center justify-between px-4 py-3 border-b " +
        (isDark ? "bg-zinc-950 border-zinc-800" : "bg-white border-gray-100")}>
        <div className="flex items-center gap-2">
          <img src={logoBsic} alt="BSIC" className="w-7 h-7" />
          <p className={"font-bold text-sm " + (isDark ? "text-white" : "text-gray-800")}>CREDISCORE</p>
        </div>
        <button onClick={() => setMobileOpen(true)}
          className={"p-2 rounded-lg border " + (isDark ? "border-zinc-800 text-zinc-400" : "border-gray-200 text-gray-500")}>
          <Menu size={18} />
        </button>
      </div>

      {/* MOBILE drawer */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <div className={"absolute left-0 top-0 h-full w-72 flex flex-col " + sidebarClass}>
            <div className={"flex items-center justify-between px-5 py-5 border-b " + (isDark ? "border-zinc-800" : "border-gray-100")}>
              <div className="flex items-center gap-2.5">
                <img src={logoBsic} alt="BSIC" className="w-7 h-7" />
                <p className={"font-bold text-sm " + (isDark ? "text-white" : "text-gray-800")}>CREDISCORE</p>
              </div>
              <button onClick={() => setMobileOpen(false)}
                className={"p-1.5 rounded-lg " + (isDark ? "text-zinc-500" : "text-gray-400")}>
                <X size={17} />
              </button>
            </div>
            <nav className="flex-1 px-3 py-2 space-y-0.5 overflow-y-auto">
              <NavLinks onClose={() => setMobileOpen(false)} />
            </nav>
            <Footer onClose={() => setMobileOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}
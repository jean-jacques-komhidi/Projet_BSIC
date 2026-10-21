import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext";
import { useAuth } from "../../context/AuthContext";
import { rechercher } from "../../services/rechercheService";
import { lireRecents, ajouterRecent, depuis } from "../../utils/recents";
import {
  Search, FileText, Users, Plus, UserPlus, ClipboardCheck, LayoutDashboard, FileSearch,
  History, Bell, MessageSquare, UserCircle, UserCog, Activity, Download, Loader2,
} from "lucide-react";

const ROUGE = "#c0392b";
const VERT = "#0F6E56";
const FILTRES = [["tout", "Tout"], ["clients", "Clients"], ["analyses", "Analyses"], ["pages", "Pages"]];

const PAGES = [
  ["Tableau de bord", "/tableau-de-bord", LayoutDashboard],
  ["Analyse de crédit", "/analyse", FileSearch],
  ["Clients", "/clients", Users],
  ["Historique", "/historique", History],
  ["Notifications", "/notifications", Bell],
  ["Assistant IA", "/assistant", MessageSquare],
  ["Mon profil", "/profil", UserCircle],
];
const PAGES_ADMIN = [
  ["Utilisateurs", "/utilisateurs", UserCog],
  ["Monitoring", "/monitoring", Activity],
  ["Export des données", "/export", Download],
];

const fcfa = (n) => (n ? Number(n).toLocaleString("fr-FR", { maximumFractionDigits: 0 }) + " FCFA" : null);
const sansAccents = (t) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

function badgeDecision(decision) {
  if (decision === "REFUSE") return { texte: "Refusé", couleur: ROUGE };
  if (decision === "ACCORDE") return { texte: "Accordé", couleur: VERT };
  return null;
}

export default function RechercheGlobale() {
  const { isDark } = useTheme();
  const { utilisateur } = useAuth();
  const navigate = useNavigate();
  const estAdmin = utilisateur?.role === "admin";
  const [ouvert, setOuvert] = useState(false);
  const [q, setQ] = useState("");
  const [filtre, setFiltre] = useState("tout");
  const [resultats, setResultats] = useState(null);
  const [chargement, setChargement] = useState(false);
  const [actif, setActif] = useState(0);
  const [recents, setRecents] = useState([]);
  const champ = useRef(null);
  const boite = useRef(null);

  // Ctrl K (ou Cmd K) ouvre la recherche depuis n'importe quelle page
  useEffect(() => {
    function clavier(e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        champ.current?.focus();
      }
    }
    window.addEventListener("keydown", clavier);
    return () => window.removeEventListener("keydown", clavier);
  }, []);

  // Fermeture au clic en dehors
  useEffect(() => {
    if (!ouvert) return undefined;
    function clic(e) { if (boite.current && !boite.current.contains(e.target)) setOuvert(false); }
    document.addEventListener("mousedown", clic);
    return () => document.removeEventListener("mousedown", clic);
  }, [ouvert]);

  // Recherche dans la base, 250 ms après la dernière frappe
  const texte = q.trim();
  useEffect(() => {
    if (texte.length < 2) return undefined;
    let annule = false;
    const minuteur = setTimeout(async () => {
      setChargement(true);
      try {
        const r = await rechercher(texte);
        if (!annule) { setResultats(r); setActif(0); }
      } catch {
        if (!annule) setResultats({ clients: [], analyses: [] });
      } finally {
        if (!annule) setChargement(false);
      }
    }, 250);
    return () => { annule = true; clearTimeout(minuteur); };
  }, [texte]);

  function fermer() {
    setOuvert(false);
    setQ("");
    setResultats(null);
    champ.current?.blur();
  }

  function aller(chemin, recent) {
    if (recent) ajouterRecent(recent);
    fermer();
    navigate(chemin);
  }

  // Sections affichées : récents, actions et pages sans texte ; résultats sinon
  const sections = (() => {
    const pages = (estAdmin ? [...PAGES, ...PAGES_ADMIN] : PAGES).map(([titre, chemin, Icone]) => ({
      cle: "p" + chemin, groupe: "pages", Icone, titre, chemin: chemin,
    }));
    if (texte.length < 2) {
      const actions = [
        { cle: "a1", Icone: Plus, titre: "Nouvelle analyse de crédit", chemin: "/analyse" },
        { cle: "a2", Icone: UserPlus, titre: "Nouveau client", chemin: "/clients?nouveau=1" },
        ...(estAdmin ? [{ cle: "a3", Icone: ClipboardCheck, titre: "Renseigner les issues des crédits", chemin: "/historique?issue=a_renseigner" }] : []),
      ];
      return [
        { titre: "Consultés récemment", groupe: "recents", items: recents.map((r) => ({
          cle: "r" + r.type + r.id, groupe: r.type === "client" ? "clients" : "analyses",
          Icone: r.type === "client" ? Users : FileText, titre: r.titre, sous: `${r.sous ? r.sous + " · " : ""}ouvert ${depuis(r.quand)}`,
          badge: r.badge, chemin: r.chemin, recent: r,
        })) },
        { titre: "Actions rapides", groupe: "actions", items: actions },
        { titre: "Pages", groupe: "pages", items: pages },
      ];
    }
    const t = sansAccents(texte);
    const clients = (resultats?.clients || []).map((c) => {
      const chemin = c.derniere_analyse_id ? `/analyse/${c.derniere_analyse_id}` : `/analyse?client=${c.id}`;
      const sous = `${c.nb_analyses} analyse${c.nb_analyses > 1 ? "s" : ""}${c.derniere_analyse ? ` · dernière le ${c.derniere_analyse}` : ""}`;
      const badge = c.risque_en_hausse ? { texte: "Risque en hausse", couleur: ROUGE } : null;
      return { cle: "c" + c.id, groupe: "clients", Icone: Users, titre: c.nom, sous, badge,
        chemin: chemin, recent: { type: "client", id: c.id, titre: c.nom, sous: "Client", badge, chemin } };
    });
    const analyses = (resultats?.analyses || []).map((a) => {
      const titre = `${a.reference}${a.client ? " · " + a.client : ""}`;
      const sous = [fcfa(a.montant), a.probabilite_defaut != null ? `probabilité de défaut ${Math.round(a.probabilite_defaut * 100)} %` : null, a.date].filter(Boolean).join(" · ");
      const badge = badgeDecision(a.decision);
      return { cle: "an" + a.id, groupe: "analyses", Icone: FileText, titre, sous, badge,
        chemin: `/analyse/${a.id}`, recent: { type: "analyse", id: a.id, titre, badge, chemin: `/analyse/${a.id}` } };
    });
    return [
      { titre: "Clients", groupe: "clients", items: clients },
      { titre: "Analyses", groupe: "analyses", items: analyses },
      { titre: "Pages", groupe: "pages", items: pages.filter((p) => sansAccents(p.titre).includes(t)) },
    ];
  })();

  const visibles = sections
    .map((sec) => ({ ...sec, items: sec.items.filter((it) => filtre === "tout" || it.groupe === filtre) }))
    .filter((sec) => sec.items.length);
  const items = visibles.flatMap((sec) => sec.items);
  const actifBorne = Math.min(actif, Math.max(items.length - 1, 0));

  function clavier(e) {
    if (e.key === "Escape") { fermer(); return; }
    if (!items.length) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActif((actifBorne + 1) % items.length); }
    if (e.key === "ArrowUp") { e.preventDefault(); setActif((actifBorne - 1 + items.length) % items.length); }
    if (e.key === "Enter") { e.preventDefault(); aller(items[actifBorne].chemin, items[actifBorne].recent); }
  }

  const c = {
    panneau: isDark ? "bg-zinc-900 border-zinc-700" : "bg-white border-gray-200",
    fort: isDark ? "text-zinc-100" : "text-gray-800",
    texte: isDark ? "text-zinc-400" : "text-gray-500",
    gris: isDark ? "text-zinc-500" : "text-gray-400",
    icone: isDark ? "bg-zinc-800 text-zinc-400" : "bg-gray-100 text-gray-500",
    actif: isDark ? "bg-zinc-800" : "bg-sky-50/70",
  };
  let index = -1;

  return (
    <div ref={boite} className="relative flex-1 max-w-xl mx-auto">
      <label className={"flex items-center gap-2.5 h-10 rounded-xl px-3.5 border transition " + (ouvert
        ? (isDark ? "bg-zinc-900 border-sky-600 ring-2 ring-sky-900/60" : "bg-white border-sky-500 ring-2 ring-sky-100")
        : (isDark ? "bg-zinc-900 border-zinc-800 hover:border-zinc-700" : "bg-gray-100 border-transparent hover:bg-gray-200/70"))}>
        <Search size={17} className={c.gris} />
        <input ref={champ} value={q} onChange={(e) => { setQ(e.target.value); setActif(0); if (e.target.value.trim().length < 2) setResultats(null); }}
          onFocus={() => { setRecents(lireRecents()); setOuvert(true); }} onKeyDown={clavier}
          placeholder="Rechercher un client, une référence, une page…" aria-label="Recherche globale"
          className={"flex-1 min-w-0 bg-transparent text-sm outline-none " + c.fort + (isDark ? " placeholder-zinc-500" : " placeholder-gray-400")} />
        {chargement ? <Loader2 size={15} className={"animate-spin " + c.gris} />
          : <kbd className={"text-[11px] rounded-md border px-1.5 py-0.5 font-sans " + (isDark ? "border-zinc-700 text-zinc-500" : "border-gray-200 bg-white text-gray-400")}>Ctrl K</kbd>}
      </label>

      {ouvert && (
        <div className={"absolute top-12 left-0 right-0 rounded-2xl border shadow-xl overflow-hidden z-50 " + c.panneau}>
          <div className="flex gap-1.5 px-4 pt-3 pb-1">
            {FILTRES.map(([cle, libelle]) => (
              <button key={cle} type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => { setFiltre(cle); setActif(0); }}
                className={"text-xs rounded-full border px-2.5 py-1 transition " + (filtre === cle
                  ? (isDark ? "bg-sky-950 border-sky-800 text-sky-300 font-semibold" : "bg-sky-50 border-sky-200 text-sky-700 font-semibold")
                  : (isDark ? "border-zinc-700 text-zinc-400" : "border-gray-200 text-gray-500"))}>{libelle}</button>
            ))}
          </div>
          <div className="max-h-[60vh] overflow-y-auto pb-1">
            {visibles.length === 0 && (
              <p className={"px-4 py-6 text-sm text-center " + c.texte}>
                {texte.length >= 2 && !chargement ? `Aucun résultat pour « ${texte} ».` : "Tapez au moins deux lettres."}
              </p>
            )}
            {visibles.map((sec) => (
              <div key={sec.titre}>
                <p className={"text-[11px] uppercase tracking-wider px-4 pt-3 pb-1 " + c.gris}>{sec.titre}</p>
                {sec.items.map((it) => {
                  index += 1;
                  const i = index;
                  return (
                    <button key={it.cle} type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => aller(it.chemin, it.recent)}
                      onMouseEnter={() => setActif(i)}
                      className={"w-full flex items-center gap-3 px-4 py-2 text-left " + (i === actifBorne ? c.actif : "")}>
                      <span className={"w-8 h-8 rounded-lg flex items-center justify-center shrink-0 " + c.icone}><it.Icone size={16} /></span>
                      <span className="min-w-0 flex-1">
                        <span className={"block text-sm truncate " + c.fort}>{it.titre}</span>
                        {it.sous && <span className={"block text-xs truncate " + c.texte}>{it.sous}</span>}
                      </span>
                      {it.badge && (
                        <span className="text-[11px] font-semibold rounded-full px-2 py-0.5 shrink-0"
                          style={{ color: it.badge.couleur, background: it.badge.couleur + (isDark ? "30" : "14") }}>{it.badge.texte}</span>
                      )}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
          <div className={"flex gap-4 text-[11px] px-4 py-2 border-t " + (isDark ? "border-zinc-800 " : "border-gray-100 ") + c.gris}>
            <span>↑↓ naviguer</span><span>Entrée ouvrir</span><span>Échap fermer</span>
          </div>
        </div>
      )}
    </div>
  );
}

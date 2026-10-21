import { useState, useRef, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import Header from "../components/ui/Header";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  getConversations, creerConversation, getConversation,
  envoyerMessageFlux, supprimerConversation,
} from "../services/chatbotService";
import { telechargerPdf } from "../services/analyseService";
import { rechercher } from "../services/rechercheService";
import {
  Send, Sparkles, Plus, Trash2, Menu, Loader2, Search, FileDown, FileText, Users, Paperclip, X, Lock,
} from "lucide-react";

// CrediBot insère [PDF:42] dans sa réponse pour proposer la fiche de
// l'analyse n°42 : on retire ces marqueurs du texte et on affiche un bouton.
const MOTIF_PDF = /\[PDF:(\d+)\]/g;
const MAX_BOUTONS_PDF = 3;

function extrairePdf(contenu, enCours) {
  const ids = [...new Set([...contenu.matchAll(MOTIF_PDF)].map((m) => m[1]))].slice(0, MAX_BOUTONS_PDF);
  let texte = contenu.replace(MOTIF_PDF, "");
  // Pendant l'écriture, un marqueur peut être à moitié arrivé ("[PDF:4")
  if (enCours) texte = texte.replace(/\[(P(D(F(:\d*)?)?)?)?$/, "");
  return { texte: texte.trim(), ids };
}

const SUGGESTIONS = [
  "Donne-moi la liste des clients",
  "Quel est le client le plus dangereux ?",
  "Quel est le client le plus stable ?",
  "Donne-moi la fiche PDF du client le plus dangereux",
];

function grouperParDate(conversations) {
  const maintenant = new Date();
  const aujourdhui = new Date(maintenant.getFullYear(), maintenant.getMonth(), maintenant.getDate());
  const hier = new Date(aujourdhui); hier.setDate(hier.getDate() - 1);
  const septJours = new Date(aujourdhui); septJours.setDate(septJours.getDate() - 7);
  const groupes = { "Aujourd'hui": [], "Hier": [], "7 derniers jours": [], "Plus ancien": [] };
  conversations.forEach((c) => {
    const d = new Date(c.date_maj);
    if (d >= aujourdhui) groupes["Aujourd'hui"].push(c);
    else if (d >= hier) groupes["Hier"].push(c);
    else if (d >= septJours) groupes["7 derniers jours"].push(c);
    else groupes["Plus ancien"].push(c);
  });
  return groupes;
}

export default function AssistantPage() {
  const { isDark } = useTheme();
  const { utilisateur } = useAuth();
  const [searchParams] = useSearchParams();
  const analyseIdParam = searchParams.get("analyse");

  const [conversations, setConversations] = useState([]);
  const [convActive, setConvActive] = useState(null);
  const [saisie, setSaisie] = useState("");
  const [chargement, setChargement] = useState(false);
  const [panneauOuvert, setPanneauOuvert] = useState(false);
  const [rechercheConv, setRechercheConv] = useState("");
  // Dossier joint : { id, reference, client } (reference inconnue tant que le serveur ne l'a pas donnée)
  const [dossier, setDossier] = useState(null);
  const finRef = useRef(null);
  const dejaTraite = useRef(false);

  async function chargerListe() {
    try { setConversations(await getConversations()); } catch {}
  }
  useEffect(() => { chargerListe(); }, []);
  // Défilement vers le bas : instantané pendant l'écriture (sinon l'animation
  // saccade à chaque morceau reçu), fluide le reste du temps.
  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: chargement ? "auto" : "smooth" });
  }, [convActive?.messages, chargement]);

  // Si on arrive avec ?analyse=ID, ouvrir une conversation contextuelle sur ce dossier
  useEffect(() => {
    if (analyseIdParam && !dejaTraite.current) {
      dejaTraite.current = true;
      (async () => {
        try {
          const conv = await creerConversation();
          setConvActive({ id: conv.id, titre: conv.titre, messages: [] });
          setDossier({ id: Number(analyseIdParam) });
          chargerListe();
          setTimeout(() => {
            envoyerAvecAnalyse("Peux-tu m'expliquer cette décision de crédit et comment le client pourrait améliorer son profil ?", conv.id, Number(analyseIdParam));
          }, 300);
        } catch {}
      })();
    }
  }, [analyseIdParam]);

  async function ouvrirConversation(id) {
    try {
      const conv = await getConversation(id);
      setConvActive(conv); setDossier(conv.dossier || null); setPanneauOuvert(false);
    } catch {}
  }
  async function nouvelleConversation() {
    try {
      const conv = await creerConversation();
      setConvActive({ id: conv.id, titre: conv.titre, messages: [] });
      setDossier(null);
      chargerListe(); setPanneauOuvert(false);
    } catch {}
  }
  async function supprimer(id, e) {
    e.stopPropagation();
    if (!confirm("Supprimer cette conversation ?")) return;
    try {
      await supprimerConversation(id);
      if (convActive?.id === id) setConvActive(null);
      chargerListe();
    } catch {}
  }

  // Ajoute une bulle CrediBot vide, puis la remplit au fur et à mesure que la
  // réponse arrive (streaming), comme dans ChatGPT ou Claude.
  async function repondreEnFlux(convId, texte, analyseId) {
    const majReponse = (contenu, enCours) => setConvActive((c) => {
      const msgs = [...c.messages];
      msgs[msgs.length - 1] = { role: "assistant", contenu, enCours };
      return { ...c, messages: msgs };
    });
    setConvActive((c) => ({ ...c, messages: [...c.messages, { role: "assistant", contenu: "", enCours: true }] }));
    try {
      const final = await envoyerMessageFlux(convId, texte, analyseId, (t) => majReponse(t, true));
      majReponse(final.trim() || "Désolé, aucune réponse n'a été reçue.", false);
      chargerListe();
      // Le serveur connaît la référence et le client du dossier joint
      if (analyseId) {
        try {
          const conv = await getConversation(convId);
          setDossier((d) => (d && d.id === analyseId ? conv.dossier || d : d));
        } catch { /* l'étiquette garde le numéro */ }
      }
    } catch {
      majReponse("Désolé, une erreur est survenue.", false);
    }
  }

  // Envoi avec une analyse liée (mode RAG), utilisé au démarrage contextuel
  async function envoyerAvecAnalyse(question, convId, analyseId) {
    const texte = question.trim();
    if (!texte) return;
    setChargement(true);
    setConvActive((c) => ({ ...c, messages: [...(c?.messages || []), { role: "user", contenu: texte }] }));
    try { await repondreEnFlux(convId, texte, analyseId); }
    finally { setChargement(false); }
  }

  async function envoyer(question) {
    const texte = (question || saisie).trim();
    if (!texte || chargement) return;
    let conv = convActive;
    if (!conv) {
      try { const n = await creerConversation(); conv = { id: n.id, titre: n.titre, messages: [] }; setConvActive(conv); }
      catch { return; }
    }
    const messagesAvant = [...(conv.messages || []), { role: "user", contenu: texte }];
    setConvActive({ ...conv, messages: messagesAvant });
    setSaisie(""); setChargement(true);
    try { await repondreEnFlux(conv.id, texte, dossier?.id ?? null); }
    finally { setChargement(false); }
  }
  function gererTouche(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); envoyer(); }
  }

  const messages = convActive?.messages || [];
  const conversationVide = messages.length === 0;
  const prenom = utilisateur?.nom?.split(" ")[0] || "";
  const heure = new Date().getHours();
  const salutation = heure < 18 ? "Bonjour" : "Bonsoir";

  const convFiltrees = conversations.filter((c) =>
    !rechercheConv.trim() || c.titre.toLowerCase().includes(rechercheConv.toLowerCase())
  );
  const groupes = grouperParDate(convFiltrees);
  const propsSaisie = { saisie, setSaisie, gererTouche, envoyer, chargement, dossier, setDossier, isDark };

  return (
    <div>
      <Header title="Assistant IA" subtitle="Posez vos questions en langage naturel" />

      <div className={"rounded-2xl border flex overflow-hidden " +
        (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm")}
        style={{ height: "calc(100vh - 180px)" }}>

        {/* Panneau conversations */}
        <div className={"w-64 border-r flex-col shrink-0 " +
          (panneauOuvert ? "flex absolute inset-y-0 left-0 z-20 " : "hidden lg:flex ") +
          (isDark ? "bg-zinc-950 border-zinc-800" : "bg-gray-50/70 border-gray-100")}>
          <div className="p-3 space-y-2.5">
            <button onClick={nouvelleConversation}
              className={"w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm font-semibold border transition " +
                (isDark ? "bg-zinc-900 border-zinc-700 text-zinc-100 hover:bg-zinc-800" : "bg-white border-gray-200 text-gray-800 hover:bg-gray-50")}>
              <Plus size={16} /> Nouvelle conversation
            </button>
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                value={rechercheConv}
                onChange={(e) => setRechercheConv(e.target.value)}
                placeholder="Rechercher une conversation"
                className={"w-full pl-8 pr-3 py-2 rounded-lg text-xs outline-none focus:ring-1 focus:ring-blue-500 border " +
                  (isDark ? "bg-zinc-900 border-zinc-800 text-white" : "bg-white border-gray-200 text-gray-700")}
              />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto px-2 pb-2">
            {convFiltrees.length === 0 ? (
              <p className={"text-center text-xs py-6 " + (isDark ? "text-zinc-600" : "text-gray-400")}>Aucune conversation</p>
            ) : (
              Object.entries(groupes).map(([periode, convs]) =>
                convs.length === 0 ? null : (
                  <div key={periode} className="mb-3">
                    <p className={"px-3 pt-2 pb-1.5 text-[11px] font-semibold " + (isDark ? "text-zinc-500" : "text-gray-400")}>{periode}</p>
                    <div className="space-y-0.5">
                      {convs.map((c) => {
                        const active = convActive?.id === c.id;
                        return (
                          <div key={c.id} onClick={() => ouvrirConversation(c.id)}
                            className={"group flex items-start gap-2 px-3 py-2 rounded-lg cursor-pointer transition " +
                              (active ? (isDark ? "bg-blue-500/15" : "bg-blue-50") : (isDark ? "hover:bg-zinc-900" : "hover:bg-white"))}>
                            <div className="flex-1 min-w-0">
                              <p className={"text-[13px] truncate " + (active
                                ? (isDark ? "text-blue-300 font-medium" : "text-blue-700 font-medium")
                                : (isDark ? "text-zinc-300" : "text-gray-700"))}>{c.titre}</p>
                              {c.apercu && (
                                <p className={"text-[11px] truncate mt-0.5 " + (active
                                  ? (isDark ? "text-blue-300/70" : "text-blue-500/80")
                                  : (isDark ? "text-zinc-500" : "text-gray-400"))}>{c.apercu}</p>
                              )}
                            </div>
                            <button onClick={(e) => supprimer(c.id, e)} title="Supprimer la conversation"
                              className="opacity-0 group-hover:opacity-100 focus:opacity-100 transition text-red-400 hover:text-red-500 mt-0.5">
                              <Trash2 size={12} />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )
              )
            )}
          </div>
          <div className={"border-t px-4 py-3 flex gap-2 text-[11px] leading-snug " +
            (isDark ? "border-zinc-800 text-zinc-500" : "border-gray-100 text-gray-500")}>
            <Lock size={13} className="shrink-0 mt-0.5" />
            <span>Les noms des clients sont remplacés par des codes avant l'envoi à l'IA.</span>
          </div>
        </div>

        {/* Zone principale */}
        <div className="flex-1 flex flex-col min-w-0">
          <button onClick={() => setPanneauOuvert(!panneauOuvert)}
            className={"lg:hidden flex items-center gap-2 px-4 py-2 text-sm border-b " +
              (isDark ? "border-zinc-800 text-zinc-400" : "border-gray-100 text-gray-500")}>
            <Menu size={16} /> Conversations
          </button>

          {conversationVide ? (
            <div className="flex-1 flex flex-col items-center justify-center px-4">
              <div className="w-full max-w-xl text-center">
                <div className="flex justify-center mb-6">
                  <div className="h-16 w-16 rounded-full animate-pulse"
                    style={{ background: "radial-gradient(circle at 30% 30%, #7db8e8, #2E86C1 60%, #1B4F72)", boxShadow: "0 8px 30px rgba(46,134,193,0.35)" }} />
                </div>
                <h1 className={"text-2xl lg:text-3xl font-bold mb-2 " + (isDark ? "text-white" : "text-gray-800")}>
                  {salutation}{prenom ? `, ${prenom}` : ""}
                </h1>
                <p className="text-2xl lg:text-3xl font-bold mb-8">
                  <span className={isDark ? "text-zinc-500" : "text-gray-400"}>Comment puis-je </span>
                  <span style={{ color: "#2E86C1" }}>vous aider ?</span>
                </p>
                <div className="mb-6 text-left">
                  <Saisie {...propsSaisie} lignes={2} />
                </div>
                <div className="flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} onClick={() => envoyer(s)}
                      className={"text-xs px-3 py-2 rounded-full border transition " +
                        (isDark ? "border-zinc-800 text-zinc-400 hover:bg-zinc-800" : "border-gray-200 text-gray-500 hover:bg-gray-50")}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              <div className="flex-1 overflow-y-auto">
                <div className="max-w-2xl mx-auto py-6 px-4 space-y-6">
                  {messages.map((msg, i) => <MessageClaude key={i} msg={msg} isDark={isDark} />)}
                  <div ref={finRef} />
                </div>
              </div>
              <div className={"border-t p-4 " + (isDark ? "border-zinc-800" : "border-gray-100")}>
                <div className="max-w-2xl mx-auto">
                  <Saisie {...propsSaisie} lignes={1} />
                  <p className={"text-center text-[11px] mt-2 " + (isDark ? "text-zinc-600" : "text-gray-400")}>
                    CrediBot peut se tromper : vérifiez les chiffres dans le dossier avant toute décision.
                  </p>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

const ROUGE = "#c0392b";
const ORANGE = "#d97706";
const VERT = "#0F6E56";
// Mêmes seuils que le modèle : refus au-delà de 70 %, risque faible sous 40 %
const couleurRisque = (p) => (p >= 0.7 ? ROUGE : p >= 0.4 ? ORANGE : VERT);

// Zone de saisie : texte, dossier joint (étiquette) et bouton « Joindre un dossier »
function Saisie({ saisie, setSaisie, gererTouche, envoyer, chargement, dossier, setDossier, isDark, lignes }) {
  const [menuOuvert, setMenuOuvert] = useState(false);
  return (
    <div className="relative">
      <div className={"rounded-2xl border transition focus-within:ring-2 " +
        (isDark ? "bg-zinc-800 border-zinc-700 focus-within:ring-blue-500/30" : "bg-white border-gray-200 shadow-sm focus-within:ring-blue-100 focus-within:border-blue-300")}>
        <textarea
          value={saisie}
          onChange={(e) => setSaisie(e.target.value)}
          onKeyDown={gererTouche}
          placeholder="Posez une question à CrediBot..."
          rows={lignes}
          className={"w-full bg-transparent outline-none text-sm resize-none px-4 pt-3 pb-1 " + (isDark ? "text-white placeholder-zinc-500" : "text-gray-800")}
        />
        <div className="flex items-center gap-2 px-3 pb-2.5">
          {dossier && (
            <span className={"inline-flex items-center gap-1.5 text-xs font-medium rounded-lg pl-2 pr-1 py-1 max-w-[55%] " +
              (isDark ? "bg-blue-500/15 text-blue-300" : "bg-blue-50 text-blue-700")}
              title={dossier.client ? `${dossier.reference} · ${dossier.client}` : undefined}>
              <FileText size={13} className="shrink-0" />
              <span className="truncate">{dossier.reference || `Dossier n° ${dossier.id}`}</span>
              <button type="button" onClick={() => setDossier(null)} aria-label="Retirer le dossier joint"
                className={"rounded p-0.5 " + (isDark ? "hover:bg-blue-500/20" : "hover:bg-blue-100")}>
                <X size={12} />
              </button>
            </span>
          )}
          <button type="button" onClick={() => setMenuOuvert((o) => !o)} aria-expanded={menuOuvert}
            className={"inline-flex items-center gap-1.5 text-xs rounded-lg border px-2.5 py-1 transition " +
              (menuOuvert
                ? (isDark ? "border-blue-500/50 text-blue-300" : "border-blue-300 text-blue-700 bg-blue-50/50")
                : (isDark ? "border-zinc-700 text-zinc-400 hover:bg-zinc-700/50" : "border-gray-200 text-gray-600 hover:bg-gray-50"))}>
            <Paperclip size={13} /> {dossier ? "Changer de dossier" : "Joindre un dossier"}
          </button>
          <button onClick={() => envoyer()} disabled={chargement || !saisie.trim()} aria-label="Envoyer"
            className="ml-auto h-9 w-9 rounded-xl flex items-center justify-center text-white transition disabled:opacity-30 shrink-0" style={{ backgroundColor: "#2E86C1" }}>
            <Send size={16} />
          </button>
        </div>
      </div>
      {menuOuvert && (
        <MenuJoindre isDark={isDark} fermer={() => setMenuOuvert(false)}
          choisir={(d) => { setDossier(d); setMenuOuvert(false); }} />
      )}
    </div>
  );
}

// Menu « Joindre un dossier » : recherche d'un dossier, ou d'un client (on joint alors son dernier dossier)
function MenuJoindre({ isDark, fermer, choisir }) {
  const [q, setQ] = useState("");
  const [resultats, setResultats] = useState(null);
  const [chargement, setChargement] = useState(false);
  const boite = useRef(null);

  useEffect(() => {
    function dehors(e) { if (boite.current && !boite.current.contains(e.target)) fermer(); }
    function echap(e) { if (e.key === "Escape") fermer(); }
    document.addEventListener("mousedown", dehors);
    document.addEventListener("keydown", echap);
    return () => { document.removeEventListener("mousedown", dehors); document.removeEventListener("keydown", echap); };
  }, [fermer]);

  useEffect(() => {
    const texte = q.trim();
    if (texte.length < 2) return undefined;
    let annule = false;
    const minuteur = setTimeout(async () => {
      setChargement(true);
      try { const r = await rechercher(texte); if (!annule) setResultats(r); }
      catch { if (!annule) setResultats({ clients: [], analyses: [] }); }
      finally { if (!annule) setChargement(false); }
    }, 250);
    return () => { annule = true; clearTimeout(minuteur); };
  }, [q]);

  const assez = q.trim().length >= 2;
  const analyses = assez ? resultats?.analyses || [] : [];
  const clients = assez ? (resultats?.clients || []).filter((c) => c.derniere_analyse_id) : [];
  const ligne = "w-full flex items-center gap-3 px-4 py-2 text-left transition " + (isDark ? "hover:bg-zinc-800" : "hover:bg-blue-50/60");
  const titre = "px-4 pt-3 pb-1 text-[11px] font-semibold " + (isDark ? "text-zinc-500" : "text-gray-400");
  const sous = "block text-[11px] " + (isDark ? "text-zinc-500" : "text-gray-500");

  return (
    <div ref={boite} className={"absolute left-0 bottom-full mb-2 w-full max-w-sm z-30 rounded-xl border overflow-hidden shadow-xl " +
      (isDark ? "bg-zinc-900 border-zinc-700" : "bg-white border-gray-200")}>
      <div className={"flex items-center gap-2 px-4 py-2.5 border-b " + (isDark ? "border-zinc-800" : "border-gray-100")}>
        <Search size={15} className="text-gray-400 shrink-0" />
        <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nom du client ou référence"
          className={"flex-1 bg-transparent outline-none text-sm " + (isDark ? "text-white" : "text-gray-800")} />
        {chargement && <Loader2 size={14} className="animate-spin text-gray-400" />}
      </div>
      <div className="max-h-64 overflow-y-auto pb-1.5">
        {!assez ? (
          <p className={"px-4 py-4 text-xs " + (isDark ? "text-zinc-500" : "text-gray-500")}>
            Tapez au moins 2 lettres : un nom de client, ou une référence comme CRED-2026-0008.
          </p>
        ) : resultats && !chargement && analyses.length === 0 && clients.length === 0 ? (
          <p className={"px-4 py-4 text-xs " + (isDark ? "text-zinc-500" : "text-gray-500")}>Aucun dossier ne correspond à « {q.trim()} ».</p>
        ) : (
          <>
            {analyses.length > 0 && <p className={titre}>Dossiers</p>}
            {analyses.map((a) => (
              <button key={`a${a.id}`} type="button" className={ligne}
                onClick={() => choisir({ id: a.id, reference: a.reference, client: a.client })}>
                <FileText size={15} className={isDark ? "text-zinc-400" : "text-gray-500"} />
                <span className="flex-1 min-w-0">
                  <span className={"block text-[13px] " + (isDark ? "text-zinc-100" : "text-gray-800")}>{a.reference}</span>
                  <span className={sous + " truncate"}>{[a.client, a.date].filter(Boolean).join(" · ")}</span>
                </span>
                {a.probabilite_defaut != null && (
                  <span className="text-xs font-semibold" style={{ color: couleurRisque(a.probabilite_defaut) }}>
                    {Math.round(a.probabilite_defaut * 100)} %
                  </span>
                )}
              </button>
            ))}
            {clients.length > 0 && <p className={titre}>Clients (dernier dossier)</p>}
            {clients.map((c) => (
              <button key={`c${c.id}`} type="button" className={ligne}
                onClick={() => choisir({ id: c.derniere_analyse_id, client: c.nom })}>
                <Users size={15} className={isDark ? "text-zinc-400" : "text-gray-500"} />
                <span className="flex-1 min-w-0">
                  <span className={"block text-[13px] truncate " + (isDark ? "text-zinc-100" : "text-gray-800")}>{c.nom}</span>
                  <span className={sous}>
                    {c.nb_analyses} analyse{c.nb_analyses > 1 ? "s" : ""}
                    {c.derniere_analyse ? ` · dernière le ${c.derniere_analyse}` : ""}
                    {c.risque_en_hausse ? " · risque en hausse" : ""}
                  </span>
                </span>
              </button>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

function BoutonPdf({ analyseId, isDark }) {
  const [etat, setEtat] = useState("pret"); // pret | chargement | erreur

  async function telecharger() {
    setEtat("chargement");
    try {
      const blob = await telechargerPdf(analyseId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `fiche_decision_${analyseId}.pdf`; a.click();
      URL.revokeObjectURL(url);
      setEtat("pret");
    } catch {
      setEtat("erreur");
    }
  }

  return (
    <button onClick={telecharger} disabled={etat === "chargement"}
      className={"inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium border transition disabled:opacity-60 " +
        (isDark ? "border-zinc-700 text-zinc-200 hover:bg-zinc-800" : "border-gray-200 text-gray-700 hover:bg-gray-50")}>
      {etat === "chargement"
        ? <Loader2 size={14} className="animate-spin" style={{ color: "#2E86C1" }} />
        : <FileDown size={14} style={{ color: "#2E86C1" }} />}
      {etat === "erreur"
        ? `Fiche n°${analyseId} indisponible`
        : `Télécharger la fiche PDF (analyse n°${analyseId})`}
    </button>
  );
}

function MessageClaude({ msg, isDark }) {
  const estUser = msg.role === "user";
  const { texte, ids } = estUser ? { texte: msg.contenu, ids: [] } : extrairePdf(msg.contenu || "", msg.enCours);
  return (
    <div className="flex gap-3">
      <div className="h-7 w-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
        style={{ backgroundColor: estUser ? (isDark ? "#3f3f46" : "#e5e7eb") : "#2E86C11a" }}>
        {estUser
          ? <span className={"text-xs font-bold " + (isDark ? "text-zinc-300" : "text-gray-600")}>V</span>
          : <Sparkles size={15} style={{ color: "#2E86C1" }} />}
      </div>
      <div className="flex-1 min-w-0">
        <p className={"text-xs font-semibold mb-1 " + (isDark ? "text-zinc-400" : "text-gray-500")}>
          {estUser ? "Vous" : "CrediBot"}
        </p>
        {estUser ? (
          <div className={"text-sm leading-relaxed whitespace-pre-wrap " + (isDark ? "text-zinc-200" : "text-gray-700")}>
            {msg.contenu}
          </div>
        ) : msg.enCours && !texte ? (
          // En attente du premier morceau de la réponse
          <Loader2 size={18} className="animate-spin mt-1" style={{ color: "#2E86C1" }} />
        ) : (
          <div className={"text-sm leading-relaxed markdown-chat " + (isDark ? "text-zinc-200" : "text-gray-700")}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{texte}</ReactMarkdown>
            {msg.enCours && (
              // Curseur clignotant pendant que CrediBot écrit
              <span className="inline-block w-2 h-4 align-middle animate-pulse rounded-sm"
                style={{ backgroundColor: "#2E86C1" }} />
            )}
            {!msg.enCours && ids.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {ids.map((id) => <BoutonPdf key={id} analyseId={id} isDark={isDark} />)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
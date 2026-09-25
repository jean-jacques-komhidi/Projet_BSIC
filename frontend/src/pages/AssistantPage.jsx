import { useState, useRef, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import Header from "../components/ui/Header";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  getConversations, creerConversation, getConversation,
  envoyerMessage, supprimerConversation,
} from "../services/chatbotService";
import {
  Send, Sparkles, Plus, Trash2, MessageSquare, Menu, Loader2, Search, FileSearch,
} from "lucide-react";

const SUGGESTIONS = [
  "Combien de crédits ont été accordés ?",
  "Quel client a le risque le plus élevé ?",
  "Combien de clients avons-nous ?",
  "Quelle est la répartition des risques ?",
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
  const [analyseLiee, setAnalyseLiee] = useState(null);
  const finRef = useRef(null);
  const dejaTraite = useRef(false);

  async function chargerListe() {
    try { setConversations(await getConversations()); } catch {}
  }
  useEffect(() => { chargerListe(); }, []);
  useEffect(() => { finRef.current?.scrollIntoView({ behavior: "smooth" }); }, [convActive?.messages, chargement]);

  // Si on arrive avec ?analyse=ID, ouvrir une conversation contextuelle sur ce dossier
  useEffect(() => {
    if (analyseIdParam && !dejaTraite.current) {
      dejaTraite.current = true;
      (async () => {
        try {
          const conv = await creerConversation();
          setConvActive({ id: conv.id, titre: conv.titre, messages: [] });
          setAnalyseLiee(analyseIdParam);
          chargerListe();
          setTimeout(() => {
            envoyerAvecAnalyse("Peux-tu m'expliquer cette décision de crédit et comment le client pourrait améliorer son profil ?", conv.id, analyseIdParam);
          }, 300);
        } catch {}
      })();
    }
  }, [analyseIdParam]);

  async function ouvrirConversation(id) {
    try { setConvActive(await getConversation(id)); setAnalyseLiee(null); setPanneauOuvert(false); } catch {}
  }
  async function nouvelleConversation() {
    try {
      const conv = await creerConversation();
      setConvActive({ id: conv.id, titre: conv.titre, messages: [] });
      setAnalyseLiee(null);
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

  // Envoi avec une analyse liée (mode RAG), utilisé au démarrage contextuel
  async function envoyerAvecAnalyse(question, convId, analyseId) {
    const texte = question.trim();
    if (!texte) return;
    setChargement(true);
    setConvActive((c) => ({ ...c, messages: [...(c?.messages || []), { role: "user", contenu: texte }] }));
    try {
      const res = await envoyerMessage(convId, texte, analyseId);
      setConvActive((c) => ({ ...c, messages: [...c.messages, res.reponse] }));
      chargerListe();
    } catch {
      setConvActive((c) => ({ ...c, messages: [...c.messages, { role: "assistant", contenu: "Désolé, une erreur est survenue." }] }));
    } finally { setChargement(false); }
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
    try {
      const res = await envoyerMessage(conv.id, texte, analyseLiee);
      setConvActive((c) => ({ ...c, messages: [...messagesAvant, res.reponse] }));
      chargerListe();
    } catch {
      setConvActive((c) => ({ ...c, messages: [...messagesAvant, { role: "assistant", contenu: "Désolé, une erreur est survenue." }] }));
    } finally { setChargement(false); }
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

  return (
    <div>
      <Header title="Assistant IA" subtitle="Posez vos questions en langage naturel" />

      <div className={"rounded-2xl border flex overflow-hidden " +
        (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm")}
        style={{ height: "calc(100vh - 180px)" }}>

        {/* Panneau conversations */}
        <div className={"w-64 border-r flex-col shrink-0 " +
          (panneauOuvert ? "flex absolute inset-y-0 left-0 z-20 " : "hidden lg:flex ") +
          (isDark ? "bg-zinc-950 border-zinc-800" : "bg-gray-50 border-gray-100")}>
          <div className="p-3">
            <button onClick={nouvelleConversation}
              className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium text-white transition hover:opacity-90"
              style={{ backgroundColor: "#2E86C1" }}>
              <Plus size={16} /> Nouvelle conversation
            </button>
          </div>
          <div className="px-3 pb-2">
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                value={rechercheConv}
                onChange={(e) => setRechercheConv(e.target.value)}
                placeholder="Rechercher..."
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
                    <p className={"px-3 py-1 text-[10px] font-semibold uppercase tracking-wider " +
                      (isDark ? "text-zinc-600" : "text-gray-400")}>{periode}</p>
                    <div className="space-y-0.5">
                      {convs.map((c) => (
                        <div key={c.id} onClick={() => ouvrirConversation(c.id)}
                          className={"group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition " +
                            (convActive?.id === c.id ? (isDark ? "bg-zinc-800" : "bg-white shadow-sm") : (isDark ? "hover:bg-zinc-900" : "hover:bg-white/60"))}>
                          <MessageSquare size={13} className={"shrink-0 " + (isDark ? "text-zinc-500" : "text-gray-400")} />
                          <span className={"flex-1 text-xs truncate " + (isDark ? "text-zinc-300" : "text-gray-600")}>{c.titre}</span>
                          <button onClick={(e) => supprimer(c.id, e)} className="opacity-0 group-hover:opacity-100 transition text-red-400 hover:text-red-500">
                            <Trash2 size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              )
            )}
          </div>
        </div>

        {/* Zone principale */}
        <div className="flex-1 flex flex-col min-w-0">
          <button onClick={() => setPanneauOuvert(!panneauOuvert)}
            className={"lg:hidden flex items-center gap-2 px-4 py-2 text-sm border-b " +
              (isDark ? "border-zinc-800 text-zinc-400" : "border-gray-100 text-gray-500")}>
            <Menu size={16} /> Conversations
          </button>

          {/* Bandeau si conversation liée à un dossier */}
          {analyseLiee && (
            <div className={"flex items-center gap-2 px-4 py-2 text-xs border-b " +
              (isDark ? "border-zinc-800 bg-zinc-800/40 text-zinc-300" : "border-gray-100 bg-blue-50/50 text-gray-600")}>
              <FileSearch size={14} style={{ color: "#2E86C1" }} />
              Conversation liée au dossier d'analyse #{analyseLiee}
            </div>
          )}

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
                <div className="mb-6">
                  <div className={"rounded-2xl border " + (isDark ? "bg-zinc-800 border-zinc-700" : "bg-white border-gray-200 shadow-sm")}>
                    <div className="flex items-end gap-2 px-3 py-2">
                      <textarea
                        value={saisie}
                        onChange={(e) => setSaisie(e.target.value)}
                        onKeyDown={gererTouche}
                        placeholder="Posez une question à CrediBot..."
                        rows={2}
                        className={"flex-1 bg-transparent outline-none text-sm resize-none py-1.5 " + (isDark ? "text-white" : "text-gray-800")}
                      />
                      <button onClick={() => envoyer()} disabled={chargement || !saisie.trim()}
                        className="h-9 w-9 rounded-xl flex items-center justify-center text-white transition disabled:opacity-30 shrink-0" style={{ backgroundColor: "#2E86C1" }}>
                        <Send size={16} />
                      </button>
                    </div>
                  </div>
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
                  {chargement && (
                    <div className="flex gap-3">
                      <div className="h-7 w-7 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: "#2E86C11a" }}>
                        <Sparkles size={15} style={{ color: "#2E86C1" }} />
                      </div>
                      <Loader2 size={18} className="animate-spin mt-1" style={{ color: "#2E86C1" }} />
                    </div>
                  )}
                  <div ref={finRef} />
                </div>
              </div>
              <div className={"border-t p-4 " + (isDark ? "border-zinc-800" : "border-gray-100")}>
                <div className="max-w-2xl mx-auto">
                  <div className={"rounded-2xl border " + (isDark ? "bg-zinc-800 border-zinc-700" : "bg-white border-gray-200 shadow-sm")}>
                    <div className="flex items-end gap-2 px-3 py-2">
                      <textarea
                        value={saisie}
                        onChange={(e) => setSaisie(e.target.value)}
                        onKeyDown={gererTouche}
                        placeholder="Posez une question à CrediBot..."
                        rows={1}
                        className={"flex-1 bg-transparent outline-none text-sm resize-none py-1.5 " + (isDark ? "text-white" : "text-gray-800")}
                      />
                      <button onClick={() => envoyer()} disabled={chargement || !saisie.trim()}
                        className="h-9 w-9 rounded-xl flex items-center justify-center text-white transition disabled:opacity-30 shrink-0" style={{ backgroundColor: "#2E86C1" }}>
                        <Send size={16} />
                      </button>
                    </div>
                  </div>
                  <p className={"text-center text-[11px] mt-2 " + (isDark ? "text-zinc-600" : "text-gray-400")}>
                    CrediBot peut faire des erreurs. Vérifiez les informations importantes.
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

function MessageClaude({ msg, isDark }) {
  const estUser = msg.role === "user";
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
        ) : (
          <div className={"text-sm leading-relaxed markdown-chat " + (isDark ? "text-zinc-200" : "text-gray-700")}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.contenu}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
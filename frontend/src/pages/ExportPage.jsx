import { useState, useEffect } from "react";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import Header from "../components/ui/Header";
import { getOptionsExport, getApercu, telechargerExport, getJournalExports } from "../services/exportService";
import { Download, Loader2, Check, AlertTriangle, ShieldCheck } from "lucide-react";

const BLEU = "#2E86C1";
const VERT = "#0F6E56";
const ORANGE = "#d97706";

const JEUX = [
  { cle: "analyses", titre: "Analyses de crédit",
    texte: "Date, agent, client, montant, revenu, échéance, probabilité de défaut, classe de risque, décision, issue réelle, version du modèle." },
  { cle: "clients", titre: "Clients",
    texte: "Nombre d'analyses, dernière décision et dernière probabilité, crédits remboursés ou en défaut, profil du client." },
  { cle: "versions", titre: "Versions du modèle",
    texte: "Algorithme, dates de mise en service et de retrait, AUC à l'entraînement et AUC réelle, statut." },
];
const DESCRIPTIONS = {
  analyses: {
    identification: "Référence de l'analyse, date, agent, client (code ou nom)",
    financier: "Montant, revenu, échéance, taux d'endettement, ancienneté d'emploi",
    modele: "Probabilité de défaut, classe de risque, décision, version du modèle",
    issue: "Remboursé, défaut ou en attente",
    profil: "Âge, profession, situation familiale",
    genre: "Féminin / masculin",
  },
  clients: {
    identification: "Client (code ou nom), date d'enregistrement, nombre d'analyses",
    modele: "Dernière probabilité de défaut et dernière décision",
    issue: "Crédits remboursés et en défaut",
    profil: "Âge, profession, situation familiale",
    genre: "Féminin / masculin",
  },
  versions: {
    identification: "Version, algorithme, statut, dates",
    modele: "AUC sur le jeu de test du socle",
    issue: "AUC réelle et nombre d'issues de validation",
  },
};

const isoDate = (d) => d.toISOString().slice(0, 10);
const aujourdhui = new Date();
const ilYaUnAn = new Date(aujourdhui.getFullYear() - 1, aujourdhui.getMonth(), aujourdhui.getDate());
const nombre = (n) => (n ?? 0).toLocaleString("fr-FR");
const cellule = (v) => (v === null || v === undefined || v === "" ? "—"
  : typeof v === "number" ? v.toLocaleString("fr-FR", { maximumFractionDigits: 4 }) : String(v));

function Titre({ numero, titre, sousTitre, s }) {
  return (
    <div className="mb-3">
      <h2 className={"text-sm font-semibold " + s.fort}>{numero}. {titre}</h2>
      {sousTitre && <p className={"text-xs mt-0.5 " + s.gris}>{sousTitre}</p>}
    </div>
  );
}

export default function ExportPage() {
  const { isDark } = useTheme();
  const { utilisateur } = useAuth();
  const [options, setOptions] = useState(null);
  const [jeu, setJeu] = useState("analyses");
  const [groupes, setGroupes] = useState(["identification", "financier", "modele", "issue"]);
  const [du, setDu] = useState(isoDate(ilYaUnAn));
  const [au, setAu] = useState(isoDate(aujourdhui));
  const [anonymiser, setAnonymiser] = useState(true);
  const [destinataire, setDestinataire] = useState("");
  const [motif, setMotif] = useState("");
  const [format, setFormat] = useState("csv");
  const [apercu, setApercu] = useState(null);
  const [chargementApercu, setChargementApercu] = useState(false);
  const [journal, setJournal] = useState([]);
  const [envoi, setEnvoi] = useState(false);
  const [message, setMessage] = useState(null);

  const s = {
    carte: "rounded-2xl border " + (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm"),
    fort: isDark ? "text-white" : "text-gray-800",
    texte: isDark ? "text-zinc-300" : "text-gray-600",
    gris: isDark ? "text-zinc-500" : "text-gray-400",
    bord: isDark ? "border-zinc-800" : "border-gray-200",
    champ: "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-sky-500/30 " +
      (isDark ? "bg-zinc-950 border-zinc-700 text-zinc-200" : "bg-white border-gray-200 text-gray-700"),
    choisi: isDark ? "border-sky-700 bg-sky-950/30" : "border-sky-500 bg-sky-50/60",
  };
  const admin = utilisateur?.role === "admin";
  const periodeActive = jeu !== "versions";
  const groupesDuJeu = options ? options.groupes.filter((g) => options.groupes_par_jeu[jeu].includes(g.cle)) : [];
  const groupesEnvoyes = groupes.filter((g) => groupesDuJeu.some((x) => x.cle === g));
  const pret = destinataire && motif.trim().length >= 5 && groupesEnvoyes.length > 0 && !envoi;

  async function chargerJournal() {
    try { setJournal(await getJournalExports()); } catch { /* le journal reste vide */ }
  }

  useEffect(() => {
    if (!admin) return;
    (async () => {
      try { setOptions(await getOptionsExport()); } catch { setMessage({ erreur: true, texte: "Impossible de charger les options d'export." }); }
      chargerJournal();
    })();
  }, [admin]);

  // Aperçu mis à jour quand les options changent
  useEffect(() => {
    if (!options || !groupesEnvoyes.length) return;
    let annule = false;
    const minuteur = setTimeout(async () => {
      setChargementApercu(true);
      try {
        const r = await getApercu({ jeu, groupes: groupesEnvoyes, anonymiser, du: periodeActive ? du || null : null, au: periodeActive ? au || null : null });
        if (!annule) setApercu(r);
      } catch { if (!annule) setApercu(null); }
      finally { if (!annule) setChargementApercu(false); }
    }, 250);
    return () => { annule = true; clearTimeout(minuteur); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options, jeu, groupesEnvoyes.join(","), anonymiser, du, au]);

  function basculerGroupe(cle) {
    setGroupes((g) => (g.includes(cle) ? g.filter((x) => x !== cle) : [...g, cle]));
  }

  async function telecharger() {
    setEnvoi(true);
    setMessage(null);
    try {
      const { fichier, nom } = await telechargerExport({
        jeu, groupes: groupesEnvoyes, anonymiser, destinataire, motif, format,
        du: periodeActive ? du || null : null, au: periodeActive ? au || null : null,
      });
      const url = window.URL.createObjectURL(fichier);
      const lien = document.createElement("a");
      lien.href = url; lien.download = nom; lien.click();
      window.URL.revokeObjectURL(url);
      setMessage({ erreur: false, texte: `${nom} téléchargé et enregistré dans le journal des exports.` });
      setMotif("");
      chargerJournal();
    } catch (e) {
      let texte = "Le téléchargement a échoué.";
      try { texte = JSON.parse(await e.response.data.text()).detail || texte; } catch { /* message par défaut */ }
      setMessage({ erreur: true, texte });
    } finally { setEnvoi(false); }
  }

  if (!admin) {
    return (
      <div>
        <Header title="Export des données" subtitle="Réservé à l'administrateur" />
        <p className={"text-sm " + s.gris}>Cette page est réservée à l'administrateur.</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl">
      <Header title="Export des données" subtitle="Fichiers pour Power BI, Excel ou une autorité de contrôle" />

      {/* 1. Jeu de données */}
      <section className={s.carte + " p-5 mb-4"}>
        <Titre s={s} numero="1" titre="Données à exporter" sousTitre="Une ligne par élément, prête pour Power BI ou Excel." />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {JEUX.map((j) => {
            const actif = jeu === j.cle;
            return (
              <button key={j.cle} type="button" onClick={() => setJeu(j.cle)}
                className={"text-left flex flex-col justify-start rounded-xl border p-3.5 transition " + (actif ? s.choisi : s.bord + (isDark ? " hover:border-zinc-600" : " hover:border-gray-300"))}>
                <span className={"flex items-center gap-2 text-sm font-semibold mb-1 " + s.fort}>
                  <span className="w-3.5 h-3.5 rounded-full shrink-0" style={{ border: actif ? `4px solid ${BLEU}` : `1.6px solid ${isDark ? "#52525b" : "#d1d5db"}` }} />
                  {j.titre}
                </span>
                <span className={"block text-xs leading-relaxed " + s.texte}>{j.texte}</span>
                {options && <span className={"block text-[11px] mt-1.5 " + s.gris}>{nombre(options.totaux[j.cle])} ligne{options.totaux[j.cle] > 1 ? "s" : ""} en base</span>}
              </button>
            );
          })}
        </div>
      </section>

      {/* 2. Colonnes */}
      <section className={s.carte + " p-5 mb-4"}>
        <Titre s={s} numero="2" titre="Colonnes à inclure"
          sousTitre="Par groupes. Le genre n'est transmis que si c'est nécessaire : le modèle ne doit pas discriminer." />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {groupesDuJeu.map((g) => {
            const coche = groupes.includes(g.cle);
            return (
              <button key={g.cle} type="button" onClick={() => basculerGroupe(g.cle)}
                className={"text-left flex flex-col justify-start rounded-xl border p-3 transition " + (coche ? s.choisi : s.bord)}>
                <span className={"flex items-center gap-2 text-sm font-semibold mb-0.5 " + s.fort}>
                  <span className="w-3.5 h-3.5 rounded flex items-center justify-center shrink-0"
                    style={coche ? { background: BLEU } : { border: `1.6px solid ${isDark ? "#52525b" : "#d1d5db"}` }}>
                    {coche && <Check size={10} color="#fff" strokeWidth={3} />}
                  </span>
                  {g.libelle}
                </span>
                <span className={"block text-xs leading-relaxed " + s.texte}>{DESCRIPTIONS[jeu][g.cle]}</span>
                {g.cle === "genre" && <span className="block text-[11px] mt-1" style={{ color: ORANGE }}>Donnée sensible, décochée par défaut</span>}
              </button>
            );
          })}
        </div>
      </section>

      {/* 3. Période, destinataire, format */}
      <section className={s.carte + " p-5 mb-4"}>
        <Titre s={s} numero="3" titre="Période, destinataire et format"
          sousTitre="Le destinataire et le motif sont obligatoires : ils sont enregistrés dans le journal des exports." />
        {periodeActive ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-3 items-end">
            <label className="block"><span className={"block text-xs font-medium mb-1.5 " + s.texte}>Du</span>
              <input type="date" value={du} max={au || undefined} onChange={(e) => setDu(e.target.value)} className={s.champ} /></label>
            <label className="block"><span className={"block text-xs font-medium mb-1.5 " + s.texte}>Au</span>
              <input type="date" value={au} min={du || undefined} onChange={(e) => setAu(e.target.value)} className={s.champ} /></label>
            <div className="md:col-span-2">
              <span className={"block text-xs font-medium mb-1.5 " + s.texte}>Noms des clients</span>
              <button type="button" onClick={() => setAnonymiser((a) => !a)}
                className={"w-full flex items-center gap-3 rounded-lg border px-3 py-2 text-left " + s.bord}>
                <span className="relative w-8 h-[18px] rounded-full shrink-0 transition" style={{ background: anonymiser ? VERT : (isDark ? "#3f3f46" : "#d1d5db") }}>
                  <span className="absolute top-0.5 w-3.5 h-3.5 rounded-full bg-white transition-all" style={{ left: anonymiser ? 16 : 2 }} />
                </span>
                <span>
                  <span className={"block text-sm " + s.fort}>{anonymiser ? "Anonymisés" : "Noms réels"}</span>
                  <span className={"block text-[11px] " + s.gris}>{anonymiser ? "Chaque nom est remplacé par un code (CLI-0012)" : "Les noms des clients figurent dans le fichier"}</span>
                </span>
              </button>
            </div>
          </div>
        ) : (
          <p className={"text-xs mb-3 " + s.gris}>Toutes les versions du modèle sont exportées ; ce fichier ne contient aucune donnée de client.</p>
        )}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-3">
          <label className="block"><span className={"block text-xs font-medium mb-1.5 " + s.texte}>Destinataire</span>
            <select value={destinataire} onChange={(e) => setDestinataire(e.target.value)} className={s.champ}>
              <option value="">Choisir…</option>
              {options?.destinataires.map((d) => <option key={d} value={d}>{d}</option>)}
            </select></label>
          <label className="block"><span className={"block text-xs font-medium mb-1.5 " + s.texte}>Motif</span>
            <input value={motif} onChange={(e) => setMotif(e.target.value)} maxLength={300}
              placeholder="Ex. : tableau de bord mensuel du risque de crédit" className={s.champ} /></label>
        </div>
        <div className={"flex flex-wrap items-center justify-between gap-3 mt-4 pt-4 border-t " + (isDark ? "border-zinc-800" : "border-gray-100")}>
          <div className="flex gap-2">
            {[["csv", "CSV (Power BI)"], ["xlsx", "Excel (.xlsx)"]].map(([cle, libelle]) => (
              <button key={cle} type="button" onClick={() => setFormat(cle)}
                className={"rounded-lg border px-3 py-2 text-xs font-medium transition " + (format === cle ? s.choisi + " text-sky-600" : s.bord + " " + s.texte)}>
                {libelle}
              </button>
            ))}
          </div>
          <button type="button" onClick={telecharger} disabled={!pret}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ backgroundColor: BLEU }}>
            {envoi ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />} Télécharger
          </button>
        </div>
        {message && (
          <p className="flex items-center gap-2 text-xs mt-3 font-medium" style={{ color: message.erreur ? "#c0392b" : VERT }}>
            {message.erreur ? <AlertTriangle size={14} /> : <ShieldCheck size={14} />} {message.texte}
          </p>
        )}
      </section>

      {/* Aperçu */}
      <section className={s.carte + " mb-6 overflow-hidden"}>
        <div className="flex items-center justify-between px-5 pt-4 pb-2.5">
          <h2 className={"text-sm font-semibold " + s.fort}>Aperçu</h2>
          <span className={"text-xs " + s.gris}>
            {chargementApercu ? "Mise à jour…" : apercu ? `${Math.min(5, apercu.total)} premières lignes sur ${nombre(apercu.total)}, ${apercu.colonnes.length} colonnes` : ""}
          </span>
        </div>
        <div className="overflow-x-auto">
          {apercu && apercu.lignes.length ? (
            <table className="w-full text-xs">
              <thead><tr className={isDark ? "bg-zinc-800/40" : "bg-gray-50"}>
                {apercu.colonnes.map((c) => <th key={c} className={"text-left font-medium px-3 py-2 whitespace-nowrap " + s.gris}>{c}</th>)}
              </tr></thead>
              <tbody>
                {apercu.lignes.map((l, i) => (
                  <tr key={i} className={"border-t " + (isDark ? "border-zinc-800" : "border-gray-50")}>
                    {apercu.colonnes.map((c) => <td key={c} className={"px-3 py-2 whitespace-nowrap " + s.texte}>{cellule(l[c])}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className={"px-5 pb-4 text-xs " + s.gris}>{groupesEnvoyes.length ? "Aucune ligne sur cette période." : "Choisissez au moins un groupe de colonnes."}</p>
          )}
        </div>
        <p className={"text-xs px-5 py-3 border-t " + (isDark ? "border-zinc-800 " : "border-gray-100 ") + s.texte}>
          Fichier joint : <span className={"font-semibold " + s.fort}>dictionnaire des données</span> (signification, unité et valeurs possibles de chaque colonne).
          {format === "csv" ? " En CSV : deux fichiers dans un .zip, séparateur « ; », accents conservés." : " En Excel : une feuille « Données » et une feuille « Dictionnaire »."}
        </p>
      </section>

      {/* Journal */}
      <div className="flex items-baseline justify-between mb-3">
        <p className={"text-xs uppercase tracking-wider font-medium " + s.gris}>Derniers exports</p>
        <p className={"text-xs " + s.gris}>Chaque export est enregistré : qui, quand, quelles données, pour qui et pourquoi</p>
      </div>
      <div className={s.carte + " overflow-x-auto mb-6"}>
        {journal.length === 0 ? (
          <p className={"text-center py-8 text-sm " + s.gris}>Aucun export pour l'instant.</p>
        ) : (
          <table className="w-full min-w-170">
            <thead><tr className={"border-b " + (isDark ? "border-zinc-800" : "border-gray-100")}>
              {["Date", "Par", "Données", "Destinataire et motif", "Clients", "Lignes"].map((h, i) => (
                <th key={h} className={(i === 5 ? "text-center " : "text-left ") + "text-xs uppercase tracking-wider font-medium px-4 py-2.5 " + s.gris}>{h}</th>
              ))}
            </tr></thead>
            <tbody>
              {journal.map((e) => (
                <tr key={e.id} className={"border-t " + (isDark ? "border-zinc-800/50" : "border-gray-50")}>
                  <td className={"px-4 py-3 text-xs whitespace-nowrap " + s.texte}>{e.date}</td>
                  <td className={"px-4 py-3 text-xs " + s.texte}>{e.auteur}</td>
                  <td className={"px-4 py-3 text-xs " + s.texte}>{e.donnees} <span className={s.gris}>({e.format === "xlsx" ? "Excel" : "CSV"})</span></td>
                  <td className={"px-4 py-3 text-xs " + s.texte}><span className={"font-medium " + s.fort}>{e.destinataire}</span><span className="block">{e.motif}</span></td>
                  <td className={"px-4 py-3 text-xs " + s.texte}>
                    {e.donnees === "Versions du modèle" ? "—" : e.anonymise ? "Anonymisés" : "Noms réels"}
                    {e.genre_inclus && <span className="block text-[11px]" style={{ color: ORANGE }}>genre inclus</span>}
                  </td>
                  <td className={"px-4 py-3 text-xs text-center " + s.texte}>{nombre(e.nb_lignes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

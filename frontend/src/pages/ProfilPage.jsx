import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import Header from "../components/ui/Header";
import { modifierMonProfil, getMesStatistiques, changerMotDePasse } from "../services/authService";
import {
  User, Mail, Shield, Calendar, Lock, Clock, Sun, Globe, Cpu, BarChart3, Check,
  ChevronRight, ArrowLeft, Eye, EyeOff, ShieldCheck, ShieldAlert, Loader2, AlertTriangle,
} from "lucide-react";

const BLEU = "#2E86C1";
const VERT = "#0F6E56";
const ORANGE = "#b45309";
const ROUGE = "#c0392b";

const ETATS_MODELE = {
  ok: ["Sous contrôle", VERT],
  surveiller: ["À surveiller", ORANGE],
  alerte: ["Réentraînement recommandé", ROUGE],
};

// Règles du mot de passe (vérifiées aussi par le serveur)
function regles(mdp, nom, email) {
  const bas = mdp.toLowerCase();
  const mots = (nom || "").toLowerCase().split(/\s+/).filter((m) => m.length >= 3);
  if (email) mots.push(email.split("@")[0].toLowerCase());
  return [
    ["Au moins 8 caractères", mdp.length >= 8],
    ["Une majuscule et une minuscule", /[A-ZÀ-Ý]/.test(mdp) && /[a-zß-ÿ]/.test(mdp)],
    ["Un chiffre", /\d/.test(mdp)],
    ["Différent de votre nom et de votre e-mail", mdp.length > 0 && !mots.some((m) => bas.includes(m))],
  ];
}

const virgule = (x, d = 3) => (x === null || x === undefined ? "—" : Number(x).toFixed(d).replace(".", ","));

function Carte({ titre, description, children, s }) {
  return (
    <section className={s.carte + " mb-4 overflow-hidden"}>
      <div className="px-6 pt-5 pb-3">
        <h2 className={"text-[17px] font-medium " + s.fort}>{titre}</h2>
        {description && <p className={"text-sm mt-0.5 " + s.texte}>{description}</p>}
      </div>
      {children}
    </section>
  );
}

function Ligne({ Icone, libelle, valeur, aide, onClick, s, children }) {
  const contenu = (
    <>
      <Icone size={19} className={"col-start-1 row-start-1 row-span-2 sm:row-span-1 self-start sm:self-center mt-0.5 sm:mt-0 " + s.icone} strokeWidth={1.7} />
      <span className={"col-start-2 row-start-1 text-xs uppercase tracking-wider " + s.texte}>{libelle}</span>
      <span className={"col-start-3 row-start-1 row-span-2 sm:row-span-1 sm:col-start-4 self-center " + s.gris}>{onClick && <ChevronRight size={18} />}</span>
      <span className="min-w-0 col-start-2 row-start-2 sm:col-start-3 sm:row-start-1">
        {children || <span className={"text-sm " + s.fort}>{valeur}</span>}
        {aide && <span className={"block text-xs mt-0.5 " + s.gris}>{aide}</span>}
      </span>
    </>
  );
  const classe = "w-full grid grid-cols-[24px_1fr_20px] sm:grid-cols-[24px_180px_1fr_20px] gap-x-3 gap-y-1 items-center px-6 py-3.5 border-t text-left " + s.trait;
  return onClick
    ? <button type="button" onClick={onClick} className={classe + " transition " + s.survol}>{contenu}</button>
    : <div className={classe}>{contenu}</div>;
}

function Pastille({ texte, couleur, s }) {
  const Icone = couleur === VERT ? Check : AlertTriangle;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium rounded-full px-2.5 py-1"
      style={{ color: s.c(couleur), background: couleur + (s.sombre ? "26" : "14") }}>
      <Icone size={13} strokeWidth={2.4} /> {texte}
    </span>
  );
}

function ChampMotDePasse({ libelle, valeur, onChange, visible, basculer, s, autoFocus }) {
  return (
    <label className="block mt-4">
      <span className={"block text-sm font-medium mb-1.5 " + s.fort}>{libelle}</span>
      <span className={"flex items-center rounded-lg border focus-within:ring-2 focus-within:ring-sky-500/40 focus-within:border-sky-500 " + s.bord}>
        <input type={visible ? "text" : "password"} value={valeur} onChange={(e) => onChange(e.target.value)} autoFocus={autoFocus}
          className={"flex-1 bg-transparent px-3.5 py-3 text-sm outline-none " + s.fort} autoComplete="new-password" />
        <button type="button" onClick={basculer} className={"px-3 " + s.icone} aria-label={visible ? "Masquer" : "Afficher"}>
          {visible ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </span>
    </label>
  );
}

export default function ProfilPage() {
  const { isDark, mode, setMode } = useTheme();
  const { utilisateur, rafraichir } = useAuth();
  const navigate = useNavigate();
  const [vue, setVue] = useState("accueil");
  const [stats, setStats] = useState(null);
  const [message, setMessage] = useState(null);

  // Modification du nom
  const [editionNom, setEditionNom] = useState(false);
  const [nom, setNom] = useState("");
  const [erreurNom, setErreurNom] = useState("");

  // Changement du mot de passe
  const [ancien, setAncien] = useState("");
  const [nouveau, setNouveau] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [visibles, setVisibles] = useState({});
  const [erreurMdp, setErreurMdp] = useState("");
  const [envoi, setEnvoi] = useState(false);

  async function charger() {
    try { setStats(await getMesStatistiques()); } catch { /* statistiques indisponibles */ }
  }
  useEffect(() => {
    (async () => {
      try { setStats(await getMesStatistiques()); } catch { /* statistiques indisponibles */ }
    })();
  }, []);

  const s = {
    sombre: isDark,
    c: (couleur) => (isDark ? ({ [VERT]: "#34d399", [ORANGE]: "#fbbf24", [ROUGE]: "#f87171", [BLEU]: "#60a5fa" }[couleur] || couleur) : couleur),
    carte: "rounded-xl border " + (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-[#dadce0]"),
    fort: isDark ? "text-zinc-100" : "text-[#202124]",
    texte: isDark ? "text-zinc-400" : "text-[#5f6368]",
    gris: isDark ? "text-zinc-500" : "text-[#80868b]",
    icone: isDark ? "text-zinc-400" : "text-[#5f6368]",
    trait: isDark ? "border-zinc-800" : "border-[#e8eaed]",
    bord: isDark ? "border-zinc-700" : "border-[#dadce0]",
    survol: isDark ? "hover:bg-zinc-800/60" : "hover:bg-[#f8f9fa]",
  };

  const initiales = (utilisateur?.nom || "?").split(" ").map((m) => m[0]).slice(0, 2).join("").toUpperCase();
  const estAdmin = utilisateur?.role === "admin";
  const libelleRole = estAdmin ? "Administrateur" : "Agent de crédit";
  const accesRole = estAdmin
    ? "Toutes les pages, dont utilisateurs, monitoring et export des données"
    : "Analyse de crédit, clients, historique, assistant IA";

  // Bilan de sécurité
  const jours = stats?.jours_depuis_changement;
  const securiteOk = jours !== null && jours !== undefined && jours <= 90;
  const bilan = !stats ? null : securiteOk
    ? { titre: "Votre compte est protégé", texte: `Mot de passe changé ${jours === 0 ? "aujourd'hui" : `il y a ${jours} jour${jours > 1 ? "s" : ""}`}. Aucune action recommandée.`, couleur: VERT }
    : { titre: "Changez votre mot de passe",
        texte: jours === null || jours === undefined
          ? "La date de votre dernier changement n'est pas connue. Choisissez un mot de passe qui respecte les règles de sécurité."
          : `Votre mot de passe a été changé il y a ${jours} jours. Pensez à le renouveler tous les 3 mois.`,
        couleur: ORANGE };

  const reglesMdp = regles(nouveau, utilisateur?.nom, utilisateur?.email);
  const nbRespectees = reglesMdp.filter(([, ok]) => ok).length;
  const identiques = confirmation.length > 0 && confirmation === nouveau;
  const pret = ancien && nbRespectees === 4 && identiques && !envoi;

  function ouvrirMotDePasse() {
    setAncien(""); setNouveau(""); setConfirmation(""); setVisibles({}); setErreurMdp("");
    setMessage(null);
    setVue("motdepasse");
    window.scrollTo(0, 0);
  }

  async function enregistrerNom() {
    setErreurNom("");
    try {
      await modifierMonProfil({ nom });
      await rafraichir();
      setEditionNom(false);
      setMessage("Votre nom a été mis à jour.");
    } catch (e) {
      const d = e?.response?.data?.detail;
      setErreurNom(typeof d === "string" ? d : "Modification impossible.");
    }
  }

  async function enregistrerMotDePasse() {
    setErreurMdp("");
    setEnvoi(true);
    try {
      await changerMotDePasse(ancien, nouveau);
      await charger();
      setVue("accueil");
      setMessage("Votre mot de passe a été changé.");
      window.scrollTo(0, 0);
    } catch (e) {
      const d = e?.response?.data?.detail;
      setErreurMdp(typeof d === "string" ? d : "Changement impossible.");
    } finally { setEnvoi(false); }
  }

  // ---------------------------------------------------------------------
  // Écran « Mot de passe »
  // ---------------------------------------------------------------------
  if (vue === "motdepasse") {
    const basculer = (cle) => () => setVisibles((v) => ({ ...v, [cle]: !v[cle] }));
    const couleurForce = nbRespectees <= 1 ? ROUGE : nbRespectees <= 3 ? ORANGE : VERT;
    const libelleForce = ["", "faible", "moyenne", "moyenne", "élevée"][nbRespectees];
    return (
      <div className="max-w-[620px] mx-auto">
        <Header title="Mon profil" subtitle="Gérez vos informations personnelles" />
        <button type="button" onClick={() => setVue("accueil")} className="flex items-center gap-3 mb-5">
          <ArrowLeft size={22} className={s.fort} />
          <h1 className={"text-2xl font-normal " + s.fort}>Mot de passe</h1>
        </button>
        <section className={s.carte + " p-6"}>
          <p className={"text-sm leading-relaxed " + s.texte}>
            Choisissez un mot de passe solide que vous n'utilisez pas ailleurs. Après le changement, vous resterez connecté sur cet appareil.
          </p>
          {stats?.mot_de_passe_change_le && <p className={"text-xs mt-1.5 " + s.gris}>Dernière modification le {stats.mot_de_passe_change_le}</p>}

          <ChampMotDePasse libelle="Mot de passe actuel" valeur={ancien} onChange={setAncien} visible={visibles.ancien} basculer={basculer("ancien")} s={s} autoFocus />
          <ChampMotDePasse libelle="Nouveau mot de passe" valeur={nouveau} onChange={setNouveau} visible={visibles.nouveau} basculer={basculer("nouveau")} s={s} />
          <div className="flex gap-1 mt-2">
            {[0, 1, 2, 3].map((i) => (
              <span key={i} className={"flex-1 h-1 rounded-full " + (isDark ? "bg-zinc-800" : "bg-[#e8eaed]")}
                style={i < nbRespectees ? { background: couleurForce } : {}} />
            ))}
          </div>
          {nouveau && <p className="text-xs font-medium mt-1.5" style={{ color: s.c(couleurForce) }}>Solidité : {libelleForce || "faible"}</p>}
          <ul className="mt-2 space-y-1">
            {reglesMdp.map(([texte, ok]) => (
              <li key={texte} className={"flex items-center gap-2 text-xs " + (ok ? "" : s.texte)} style={ok ? { color: s.c(VERT) } : {}}>
                {ok ? <Check size={14} strokeWidth={2.4} /> : <span className={"w-3.5 h-3.5 rounded-full border " + s.bord} />} {texte}
              </li>
            ))}
          </ul>

          <ChampMotDePasse libelle="Confirmer le nouveau mot de passe" valeur={confirmation} onChange={setConfirmation} visible={visibles.confirmation} basculer={basculer("confirmation")} s={s} />
          {confirmation && (
            <p className="flex items-center gap-2 text-xs mt-2" style={{ color: s.c(identiques ? VERT : ROUGE) }}>
              {identiques ? <><Check size={14} strokeWidth={2.4} /> Les deux mots de passe sont identiques</> : "Les deux mots de passe sont différents"}
            </p>
          )}
          {erreurMdp && <p className="text-sm mt-4" style={{ color: s.c(ROUGE) }}>{erreurMdp}</p>}

          <div className="flex justify-end items-center gap-2 mt-6">
            <button type="button" onClick={() => setVue("accueil")} className="px-4 py-2 rounded-md text-sm font-medium" style={{ color: s.c(BLEU) }}>Annuler</button>
            <button type="button" onClick={enregistrerMotDePasse} disabled={!pret}
              className="flex items-center gap-2 px-5 py-2.5 rounded-md text-sm font-medium text-white disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ background: BLEU }}>
              {envoi && <Loader2 size={15} className="animate-spin" />} Changer le mot de passe
            </button>
          </div>
        </section>
      </div>
    );
  }

  // ---------------------------------------------------------------------
  // Accueil du profil
  // ---------------------------------------------------------------------
  const etatModele = ETATS_MODELE[stats?.modele?.etat];
  return (
    <div className="max-w-[780px] mx-auto">
      <Header title="Mon profil" subtitle="Gérez vos informations personnelles" />

      <div className="text-center pt-1 pb-6">
        <div className="w-[88px] h-[88px] rounded-full mx-auto mb-3.5 flex items-center justify-center text-3xl font-semibold text-white"
          style={{ background: BLEU, boxShadow: `0 0 0 4px ${isDark ? "#09090b" : "#fff"}, 0 0 0 5px ${isDark ? "#3f3f46" : "#dadce0"}` }}>
          {initiales}
        </div>
        <h1 className={"text-[26px] font-normal " + s.fort}>Bienvenue, {utilisateur?.nom}</h1>
        <p className={"text-sm mt-1.5 " + s.texte}>
          {utilisateur?.email} · <span className={"inline-block text-xs border rounded-full px-2.5 py-0.5 align-[1px] " + s.bord}>{libelleRole}</span>
        </p>
      </div>

      {message && (
        <p className="flex items-center gap-2 text-sm font-medium rounded-lg px-4 py-3 mb-4" style={{ color: s.c(VERT), background: VERT + (isDark ? "22" : "12") }}>
          <Check size={16} /> {message}
        </p>
      )}

      {/* Bilan de sécurité */}
      {bilan && (
        <section className="rounded-xl border px-6 py-5 mb-4 flex items-center justify-between gap-4 flex-wrap"
          style={{ borderColor: bilan.couleur + "55", background: bilan.couleur + (isDark ? "14" : "0a") }}>
          <div className="flex items-center gap-3.5">
            {securiteOk ? <ShieldCheck size={30} style={{ color: s.c(VERT) }} strokeWidth={1.6} /> : <ShieldAlert size={30} style={{ color: s.c(ORANGE) }} strokeWidth={1.6} />}
            <div>
              <h2 className={"text-[17px] font-medium " + s.fort}>{bilan.titre}</h2>
              <p className={"text-sm " + s.texte}>{bilan.texte}</p>
            </div>
          </div>
          {securiteOk
            ? <Pastille texte="Vérifié" couleur={VERT} s={s} />
            : <button type="button" onClick={ouvrirMotDePasse} className="px-4 py-2 rounded-md text-sm font-medium text-white" style={{ background: BLEU }}>Changer le mot de passe</button>}
        </section>
      )}

      {/* Chiffres rapides */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
        <div className={s.carte + " p-4"}>
          <p className={"text-xs " + s.texte}>Analyses réalisées</p>
          <p className={"text-2xl font-medium " + s.fort}>{stats ? stats.analyses_realisees.toLocaleString("fr-FR") : "—"}</p>
          <p className={"text-xs " + s.texte}>sur les 12 derniers mois</p>
        </div>
        <div className={s.carte + " p-4"}>
          <p className={"text-xs " + s.texte}>Taux d'accord</p>
          <p className={"text-2xl font-medium " + s.fort}>{stats?.taux_accord != null ? `${stats.taux_accord} %` : "—"}</p>
          <div className="h-1.5 rounded-full mt-2.5 overflow-hidden" style={{ background: ROUGE + "22" }}>
            <div className="h-full rounded-full" style={{ width: `${stats?.taux_accord || 0}%`, background: VERT }} />
          </div>
        </div>
        <button type="button" onClick={() => navigate("/historique?issue=a_renseigner")} className={s.carte + " p-4 text-left transition " + s.survol}>
          <p className={"text-xs " + s.texte}>Issues à renseigner</p>
          <p className={"text-2xl font-medium " + s.fort}>{stats ? stats.issues_a_renseigner : "—"}</p>
          <p className="text-xs font-medium" style={{ color: s.c(BLEU) }}>{stats?.issues_a_renseigner ? "Voir mes dossiers ›" : "Aucun dossier en attente"}</p>
        </button>
      </div>

      <Carte s={s} titre="Informations personnelles" description="Ces informations figurent sur les fiches de décision que vous signez.">
        {editionNom ? (
          <div className={"px-6 py-4 border-t " + s.trait}>
            <label className={"block text-xs uppercase tracking-wider mb-2 " + s.texte}>Nom</label>
            <input value={nom} onChange={(e) => setNom(e.target.value)} maxLength={100} autoFocus
              className={"w-full max-w-md rounded-lg border bg-transparent px-3.5 py-2.5 text-sm outline-none focus:ring-2 focus:ring-sky-500/40 " + s.bord + " " + s.fort} />
            {erreurNom && <p className="text-xs mt-2" style={{ color: s.c(ROUGE) }}>{erreurNom}</p>}
            <div className="flex gap-2 mt-3">
              <button type="button" onClick={enregistrerNom} disabled={nom.trim().length < 2}
                className="px-4 py-2 rounded-md text-sm font-medium text-white disabled:opacity-40" style={{ background: BLEU }}>Enregistrer</button>
              <button type="button" onClick={() => setEditionNom(false)} className="px-4 py-2 rounded-md text-sm font-medium" style={{ color: s.c(BLEU) }}>Annuler</button>
            </div>
          </div>
        ) : (
          <Ligne s={s} Icone={User} libelle="Nom" valeur={utilisateur?.nom} aide="Affiché sur les fiches PDF et dans l'historique"
            onClick={() => { setNom(utilisateur?.nom || ""); setErreurNom(""); setMessage(null); setEditionNom(true); }} />
        )}
        <Ligne s={s} Icone={Mail} libelle="E-mail" valeur={utilisateur?.email} aide="Modifiable uniquement par l'administrateur" />
        <Ligne s={s} Icone={Shield} libelle="Rôle" valeur={libelleRole} aide={accesRole} />
        <Ligne s={s} Icone={Calendar} libelle="Membre depuis" valeur={stats?.membre_depuis || "—"} />
      </Carte>

      <Carte s={s} titre="Sécurité" description="Protégez l'accès aux dossiers de vos clients.">
        <Ligne s={s} Icone={Lock} libelle="Mot de passe" valeur="••••••••" onClick={ouvrirMotDePasse}
          aide={stats?.mot_de_passe_change_le ? `Dernière modification le ${stats.mot_de_passe_change_le}` : "Date de dernière modification inconnue"} />
        <Ligne s={s} Icone={Clock} libelle="Session" valeur="Valable 8 heures" aide="Vous êtes déconnecté automatiquement ensuite" />
      </Carte>

      <Carte s={s} titre="Préférences" description="L'apparence de l'application sur cet appareil.">
        <Ligne s={s} Icone={Sun} libelle="Thème">
          <span className={"inline-flex rounded-lg border overflow-hidden text-sm " + s.bord}>
            {[["clair", "Clair"], ["sombre", "Sombre"], ["systeme", "Système"]].map(([cle, libelle]) => (
              <button key={cle} type="button" onClick={() => setMode(cle)}
                className={"px-3.5 py-1.5 transition " + (mode === cle ? "font-medium" : s.texte)}
                style={mode === cle ? { background: isDark ? "#1e3a5f" : "#e8f0fe", color: isDark ? "#93c5fd" : "#1a56b0" } : {}}>
                {libelle}
              </button>
            ))}
          </span>
        </Ligne>
        <Ligne s={s} Icone={Globe} libelle="Langue" valeur="Français" />
      </Carte>

      <Carte s={s} titre="Modèle utilisé pour vos analyses" description="Le modèle qui calcule la probabilité de défaut de vos dossiers.">
        {stats?.modele ? (
          <>
            <Ligne s={s} Icone={Cpu} libelle="Version" valeur={`v${stats.modele.version} · ${stats.modele.algorithme}`}
              aide={stats.modele.mise_en_service ? `En service depuis le ${stats.modele.mise_en_service}` : null} />
            <Ligne s={s} Icone={BarChart3} libelle="Surveillance">
              <span className="flex items-center gap-2 flex-wrap">
                {etatModele ? <Pastille texte={etatModele[0]} couleur={etatModele[1]} s={s} /> : <span className={"text-sm " + s.texte}>Pas encore évaluée</span>}
                {stats.modele.auc_reelle != null && <span className={"text-xs " + s.gris}>AUC réelle {virgule(stats.modele.auc_reelle)}</span>}
              </span>
            </Ligne>
          </>
        ) : (
          <Ligne s={s} Icone={Cpu} libelle="Version" valeur="—" />
        )}
      </Carte>

      <p className={"flex items-center justify-center gap-1.5 text-xs mt-2 mb-6 " + s.gris}>
        <Lock size={13} /> Vos données et celles de vos clients sont protégées par le secret bancaire.
      </p>
    </div>
  );
}

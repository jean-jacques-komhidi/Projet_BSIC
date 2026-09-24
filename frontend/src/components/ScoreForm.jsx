import { useState, useEffect } from "react";
import { useTheme } from "../context/ThemeContext";
import { User, CreditCard, Gauge, Loader2, Lock } from "lucide-react";

const EDUCATIONS = ["Higher education", "Secondary / secondary special", "Incomplete higher", "Lower secondary"];
const PROFESSIONS = ["Core staff", "Laborers", "Managers", "Drivers", "Sales staff", "Accountants", "Medicine staff"];
const ORGANISATIONS = ["School", "Government", "Business Entity Type 3", "Self-employed", "Other", "Medicine"];
const REVENUS = ["Working", "Commercial associate", "Pensioner", "State servant"];
const CONTRATS = ["Cash loans", "Revolving loans"];
const SITUATIONS = ["Married", "Single / not married", "Widow", "Separated"];

export default function ScoreForm({ onSubmit, loading, client }) {
  const { isDark } = useTheme();

  const [form, setForm] = useState({
    AGE_ANNEES: "", CODE_GENDER: "M", NAME_FAMILY_STATUS: "Married",
    CNT_CHILDREN: 0, CNT_FAM_MEMBERS: 1, NAME_EDUCATION_TYPE: "Higher education",
    OCCUPATION_TYPE: "Core staff", ORGANIZATION_TYPE: "School",
    NAME_INCOME_TYPE: "Working", ANCIENNETE_EMPLOI_ANNEES: "", EMPLOI_ANORMAL: 0,
    AMT_INCOME_TOTAL: "", AMT_CREDIT: "", AMT_ANNUITY: "", AMT_GOODS_PRICE: "",
    NAME_CONTRACT_TYPE: "Cash loans",
    EXT_SOURCE_1: 0.5, EXT_SOURCE_2: 0.5, EXT_SOURCE_3: 0.5,
  });

  // Pré-remplir depuis le client
  useEffect(() => {
    if (client) {
      setForm((f) => ({
        ...f,
        AGE_ANNEES: client.age || f.AGE_ANNEES,
        CODE_GENDER: client.genre || f.CODE_GENDER,
        NAME_FAMILY_STATUS: client.situation_familiale || f.NAME_FAMILY_STATUS,
        OCCUPATION_TYPE: client.profession && PROFESSIONS.includes(client.profession) ? client.profession : f.OCCUPATION_TYPE,
      }));
    }
  }, [client]);

  function maj(champ, valeur) {
    setForm((f) => ({ ...f, [champ]: valeur }));
  }

  function soumettre(e) {
    e.preventDefault();
    const dossier = {
      ...form,
      AGE_ANNEES: parseFloat(form.AGE_ANNEES),
      CNT_CHILDREN: parseInt(form.CNT_CHILDREN),
      CNT_FAM_MEMBERS: parseFloat(form.CNT_FAM_MEMBERS),
      ANCIENNETE_EMPLOI_ANNEES: parseFloat(form.ANCIENNETE_EMPLOI_ANNEES),
      EMPLOI_ANORMAL: parseInt(form.EMPLOI_ANORMAL),
      AMT_INCOME_TOTAL: parseFloat(form.AMT_INCOME_TOTAL),
      AMT_CREDIT: parseFloat(form.AMT_CREDIT),
      AMT_ANNUITY: parseFloat(form.AMT_ANNUITY),
      AMT_GOODS_PRICE: parseFloat(form.AMT_GOODS_PRICE),
      EXT_SOURCE_1: parseFloat(form.EXT_SOURCE_1),
      EXT_SOURCE_2: parseFloat(form.EXT_SOURCE_2),
      EXT_SOURCE_3: parseFloat(form.EXT_SOURCE_3),
    };
    onSubmit(dossier);
  }

  const cardClass = "rounded-2xl border p-5 mb-4 " +
    (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");
  const inputClass = "w-full px-3 py-2 rounded-lg border outline-none focus:ring-2 focus:ring-blue-500 text-sm " +
    (isDark ? "bg-zinc-800 border-zinc-700 text-white" : "bg-white border-gray-200 text-gray-800");
  const labelClass = "block text-xs font-medium mb-1 " + (isDark ? "text-zinc-400" : "text-gray-600");
  const titre = "flex items-center gap-2 font-semibold text-sm mb-4 " + (isDark ? "text-white" : "text-gray-800");

  const verrou = client ? " opacity-60 cursor-not-allowed" : "";
  const cadenas = client ? <Lock size={11} className="inline text-blue-500 ml-1" /> : null;

  return (
    <form onSubmit={soumettre}>
      {/* Profil */}
      <div className={cardClass}>
        <p className={titre}><User size={16} style={{ color: "#2E86C1" }} /> Profil du demandeur</p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <div><label className={labelClass}>Âge {cadenas}</label>
            <input type="number" value={form.AGE_ANNEES} onChange={(e) => maj("AGE_ANNEES", e.target.value)} className={inputClass + verrou} required disabled={!!client} /></div>
          <div><label className={labelClass}>Genre {cadenas}</label>
            <select value={form.CODE_GENDER} onChange={(e) => maj("CODE_GENDER", e.target.value)} className={inputClass + verrou} disabled={!!client}>
              <option value="M">Masculin</option><option value="F">Féminin</option></select></div>
          <div><label className={labelClass}>Situation {cadenas}</label>
            <select value={form.NAME_FAMILY_STATUS} onChange={(e) => maj("NAME_FAMILY_STATUS", e.target.value)} className={inputClass + verrou} disabled={!!client}>
              {SITUATIONS.map((s) => <option key={s} value={s}>{s}</option>)}</select></div>
          <div><label className={labelClass}>Enfants</label>
            <input type="number" value={form.CNT_CHILDREN} onChange={(e) => maj("CNT_CHILDREN", e.target.value)} className={inputClass} min="0" /></div>
          <div><label className={labelClass}>Membres famille</label>
            <input type="number" value={form.CNT_FAM_MEMBERS} onChange={(e) => maj("CNT_FAM_MEMBERS", e.target.value)} className={inputClass} min="1" /></div>
          <div><label className={labelClass}>Ancienneté (ans)</label>
            <input type="number" value={form.ANCIENNETE_EMPLOI_ANNEES} onChange={(e) => maj("ANCIENNETE_EMPLOI_ANNEES", e.target.value)} className={inputClass} required /></div>
          <div><label className={labelClass}>Éducation</label>
            <select value={form.NAME_EDUCATION_TYPE} onChange={(e) => maj("NAME_EDUCATION_TYPE", e.target.value)} className={inputClass}>
              {EDUCATIONS.map((s) => <option key={s} value={s}>{s}</option>)}</select></div>
          <div><label className={labelClass}>Profession {cadenas}</label>
            <select value={form.OCCUPATION_TYPE} onChange={(e) => maj("OCCUPATION_TYPE", e.target.value)} className={inputClass + verrou} disabled={!!client}>
              {PROFESSIONS.map((s) => <option key={s} value={s}>{s}</option>)}</select></div>
          <div><label className={labelClass}>Employeur</label>
            <select value={form.ORGANIZATION_TYPE} onChange={(e) => maj("ORGANIZATION_TYPE", e.target.value)} className={inputClass}>
              {ORGANISATIONS.map((s) => <option key={s} value={s}>{s}</option>)}</select></div>
          <div><label className={labelClass}>Type de revenu</label>
            <select value={form.NAME_INCOME_TYPE} onChange={(e) => maj("NAME_INCOME_TYPE", e.target.value)} className={inputClass}>
              {REVENUS.map((s) => <option key={s} value={s}>{s}</option>)}</select></div>
        </div>
      </div>

      {/* Crédit */}
      <div className={cardClass}>
        <p className={titre}><CreditCard size={16} style={{ color: "#0F6E56" }} /> Caractéristiques du crédit</p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <div><label className={labelClass}>Revenu (FCFA)</label>
            <input type="number" value={form.AMT_INCOME_TOTAL} onChange={(e) => maj("AMT_INCOME_TOTAL", e.target.value)} className={inputClass} required /></div>
          <div><label className={labelClass}>Montant crédit</label>
            <input type="number" value={form.AMT_CREDIT} onChange={(e) => maj("AMT_CREDIT", e.target.value)} className={inputClass} required /></div>
          <div><label className={labelClass}>Échéance</label>
            <input type="number" value={form.AMT_ANNUITY} onChange={(e) => maj("AMT_ANNUITY", e.target.value)} className={inputClass} required /></div>
          <div><label className={labelClass}>Prix du bien</label>
            <input type="number" value={form.AMT_GOODS_PRICE} onChange={(e) => maj("AMT_GOODS_PRICE", e.target.value)} className={inputClass} required /></div>
          <div><label className={labelClass}>Type de contrat</label>
            <select value={form.NAME_CONTRACT_TYPE} onChange={(e) => maj("NAME_CONTRACT_TYPE", e.target.value)} className={inputClass}>
              {CONTRATS.map((s) => <option key={s} value={s}>{s}</option>)}</select></div>
        </div>
      </div>

      {/* Scores */}
      <div className={cardClass}>
        <p className={titre}><Gauge size={16} style={{ color: "#d97706" }} /> Scores de solvabilité (0 à 1)</p>
        <div className="grid grid-cols-3 gap-3">
          {["EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3"].map((s, i) => (
            <div key={s}>
              <label className={labelClass}>Score {i + 1}</label>
              <input type="number" step="0.01" min="0" max="1" value={form[s]}
                onChange={(e) => maj(s, e.target.value)} className={inputClass} />
            </div>
          ))}
        </div>
      </div>

      <button type="submit" disabled={loading}
        className="w-full py-3 rounded-lg font-medium text-white transition disabled:opacity-60 flex items-center justify-center gap-2"
        style={{ backgroundColor: "#2E86C1" }}>
        {loading ? <><Loader2 size={18} className="animate-spin" /> Analyse en cours...</> : "Analyser le dossier"}
      </button>
    </form>
  );
}
import { useTheme } from "../context/ThemeContext";

const LIBELLES = {
  EXT_SOURCE_1: "Score de solvabilité 1", EXT_SOURCE_2: "Score de solvabilité 2",
  EXT_SOURCE_3: "Score de solvabilité 3", AMT_INCOME_TOTAL: "Revenu",
  AMT_CREDIT: "Montant du crédit", AMT_ANNUITY: "Échéance",
  AMT_GOODS_PRICE: "Prix du bien", AGE_ANNEES: "Âge",
  ANCIENNETE_EMPLOI_ANNEES: "Ancienneté d'emploi", CNT_CHILDREN: "Nombre d'enfants",
  CNT_FAM_MEMBERS: "Taille famille", CODE_GENDER: "Genre",
  NAME_FAMILY_STATUS: "Situation familiale", NAME_EDUCATION_TYPE: "Éducation",
  OCCUPATION_TYPE: "Profession", ORGANIZATION_TYPE: "Employeur",
  NAME_INCOME_TYPE: "Type de revenu", NAME_CONTRACT_TYPE: "Type de crédit",
};
function libelle(v) {
  for (const cle in LIBELLES) if (v.startsWith(cle)) return LIBELLES[cle];
  return v.replace(/_/g, " ");
}

export default function ShapChart({ result }) {
  const { isDark } = useTheme();
  const facteurs = result.facteurs_explicatifs || [];
  if (facteurs.length === 0) return null;

  const maxContrib = Math.max(...facteurs.map((f) => Math.abs(f.contribution)), 0.001);

  const cardClass = "rounded-2xl border p-5 " +
    (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");

  return (
    <div className={cardClass + " animate-fadeUp"}>
      <p className={"font-semibold text-sm mb-1 " + (isDark ? "text-white" : "text-gray-800")}>
        Facteurs déterminants
      </p>
      <p className={"text-xs mb-4 " + (isDark ? "text-zinc-500" : "text-gray-400")}>
        Contribution de chaque variable à la décision
      </p>

      <div className="space-y-3">
        {facteurs.map((f, i) => {
          const augmente = f.contribution > 0;
          const largeur = (Math.abs(f.contribution) / maxContrib) * 100;
          const couleur = augmente ? "#c0392b" : "#0F6E56";
          return (
            <div key={i}>
              <div className="flex justify-between items-center mb-1">
                <span className={"text-xs " + (isDark ? "text-zinc-300" : "text-gray-700")}>
                  {libelle(f.variable)}
                </span>
                <span className="text-[11px] font-medium flex items-center gap-1" style={{ color: couleur }}>
                  {augmente ? "↑ augmente" : "↓ réduit"}
                </span>
              </div>
              <div className="h-2 rounded-full overflow-hidden"
                style={{ backgroundColor: isDark ? "#27272a" : "#f3f4f6" }}>
                <div className="h-full rounded-full transition-all duration-700"
                  style={{ width: largeur + "%", backgroundColor: couleur }} />
              </div>
            </div>
          );
        })}
      </div>

      <div className={"flex items-center gap-4 mt-4 pt-3 border-t text-[11px] " +
        (isDark ? "border-zinc-800 text-zinc-500" : "border-gray-100 text-gray-400")}>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: "#c0392b" }} /> Augmente le risque
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: "#0F6E56" }} /> Réduit le risque
        </span>
      </div>
    </div>
  );
}
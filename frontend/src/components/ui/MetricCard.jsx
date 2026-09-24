import { useTheme } from "../../context/ThemeContext";

const COULEURS = {
  blue: "#2E86C1",
  green: "#0F6E56",
  red: "#c0392b",
  orange: "#d97706",
};

export default function MetricCard({ title, value, suffix, subtitle, icon: Icone, color }) {
  const { isDark } = useTheme();
  const couleur = COULEURS[color] || COULEURS.blue;

  const cardClass = "rounded-2xl border p-4 lg:p-5 transition-colors animate-fadeUp " +
    (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm");

  return (
    <div className={cardClass}>
      <p className={"text-xs " + (isDark ? "text-zinc-500" : "text-gray-400")}>{title}</p>
      {/* Valeur avec l'icône à côté */}
      <div className="flex items-center gap-3 mt-1.5">
        <div className="h-10 w-10 rounded-lg flex items-center justify-center shrink-0"
          style={{ backgroundColor: couleur + "1a" }}>
          <Icone size={20} style={{ color: couleur }} />
        </div>
        <p className={"text-2xl font-bold " + (isDark ? "text-white" : "text-gray-800")}>
          {value === null ? "..." : value}{value !== null && suffix}
        </p>
      </div>
      <p className={"text-[11px] mt-1.5 " + (isDark ? "text-zinc-600" : "text-gray-400")}>{subtitle}</p>
    </div>
  );
}
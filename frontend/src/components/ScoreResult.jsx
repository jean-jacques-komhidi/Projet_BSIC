import { useTheme } from "../context/ThemeContext";
import { CheckCircle, XCircle, FileDown } from "lucide-react";
import { useEffect, useState } from "react";

// Seuils adaptés à notre backend (3 niveaux, seuil décision 70%)
// < 40%  → faible → vert
// 40-70% → moyen  → ambre
// > 70%  → élevé  → rouge
const getColor = (p) => {
  if (p < 40) return "#059669";
  if (p < 70) return "#d97706";
  return "#dc2626";
};
const getProbaColor = (p) => {
  if (p < 40) return "text-emerald-500";
  if (p < 70) return "text-amber-500";
  return "text-red-500";
};
const getBarColor = (p) => {
  if (p < 40) return "bg-emerald-500";
  if (p < 70) return "bg-amber-500";
  return "bg-red-500";
};

// ── SPEEDOMETER ──
function Speedometer({ proba, isDark }) {
  const [animated, setAnimated] = useState(0);

  useEffect(() => {
    setAnimated(0);
    const timeout = setTimeout(() => {
      let startTime = null;
      const duration = 1200;
      const animate = (now) => {
        if (!startTime) startTime = now;
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        setAnimated(Math.round(eased * proba * 10) / 10);
        if (progress < 1) requestAnimationFrame(animate);
      };
      requestAnimationFrame(animate);
    }, 100);
    return () => clearTimeout(timeout);
  }, [proba]);

  const cx = 130, cy = 110, r = 90;
  const toRad = (deg) => (deg * Math.PI) / 180;

  const arcPath = (startDeg, endDeg) => {
    const s = toRad(startDeg), e = toRad(endDeg);
    const x1 = cx + r * Math.cos(s), y1 = cy - r * Math.sin(s);
    const x2 = cx + r * Math.cos(e), y2 = cy - r * Math.sin(e);
    return "M " + x1 + " " + y1 + " A " + r + " " + r + " 0 0 1 " + x2 + " " + y2;
  };

  const pct = animated / 100;
  const colorAngle = 180 - pct * 180;
  const color = getColor(animated);
  const needleRad = toRad(180 - pct * 180);
  const nx = cx + 72 * Math.cos(needleRad);
  const ny = cy - 72 * Math.sin(needleRad);

  const markers = [
    { value: 0, label: "0%" }, { value: 40, label: "40%" },
    { value: 70, label: "70%" }, { value: 100, label: "100%" },
  ];
  // Zones adaptées à nos seuils
  const zones = [
    { from: 180, to: 180 - (40 / 100) * 180, color: "#059669" },
    { from: 180 - (40 / 100) * 180, to: 180 - (70 / 100) * 180, color: "#d97706" },
    { from: 180 - (70 / 100) * 180, to: 0, color: "#dc2626" },
  ];

  const tickColor = isDark ? "#52524e" : "#9ca3af";
  const trackColor = isDark ? "#27272a" : "#e5e7eb";
  const needleColor = isDark ? "#e4e4e7" : "#18181b";

  return (
    <div style={{ display: "flex", justifyContent: "center" }}>
      <svg width="260" height="190" viewBox="0 0 260 190">
        <path d={arcPath(180, 0)} fill="none" stroke={trackColor} strokeWidth="16" strokeLinecap="round" />
        {zones.map((z, i) => (
          <path key={i} d={arcPath(z.from, z.to)} fill="none" stroke={z.color} strokeWidth="16" strokeLinecap="butt" opacity="0.15" />
        ))}
        <path d={arcPath(180, colorAngle)} fill="none" stroke={color} strokeWidth="16" strokeLinecap="round"
          style={{ transition: "all 0.05s linear" }} />
        {markers.map(({ value, label }) => {
          const angle = toRad(180 - (value / 100) * 180);
          const lx = cx + (r + 16) * Math.cos(angle);
          const ly = cy - (r + 16) * Math.sin(angle);
          return <text key={value} x={lx} y={ly} textAnchor="middle" dominantBaseline="middle" fontSize="9" fill={tickColor}>{label}</text>;
        })}
        {/* Ligne de seuil à 70% */}
        {(() => {
          const seuilAngle = toRad(180 - (70 / 100) * 180);
          const sx1 = cx + (r - 12) * Math.cos(seuilAngle);
          const sy1 = cy - (r - 12) * Math.sin(seuilAngle);
          const sx2 = cx + (r + 8) * Math.cos(seuilAngle);
          const sy2 = cy - (r + 8) * Math.sin(seuilAngle);
          return (
            <g>
              <line x1={sx1} y1={sy1} x2={sx2} y2={sy2} stroke="#dc2626" strokeWidth="2" strokeDasharray="3,2" />
              <text x={sx2 + 2} y={sy2 - 4} fontSize="7" fill="#dc2626" textAnchor="middle">70%</text>
            </g>
          );
        })()}
        <line x1={cx} y1={cy} x2={nx} y2={ny} stroke={needleColor} strokeWidth="2" strokeLinecap="round"
          style={{ transition: "all 0.05s linear" }} />
        <circle cx={cx} cy={cy} r="6" fill={needleColor} />
        <circle cx={cx} cy={cy} r="3.5" fill={color} />
        <rect x={cx - 52} y={cy + 16} width="104" height="46" rx="8"
          fill={isDark ? "#09090b" : "#ffffff"} stroke={isDark ? "#27272a" : "#e5e7eb"} strokeWidth="1" />
        <text x={cx} y={cy + 38} textAnchor="middle" fontSize="24" fontWeight="bold" fill={color}
          style={{ transition: "fill 0.3s" }}>{animated.toFixed(1)}%</text>
        <text x={cx} y={cy + 54} textAnchor="middle" fontSize="9" fill={tickColor}>Probabilité de défaut</text>
      </svg>
    </div>
  );
}

// ── SCORE RESULT ──
export default function ScoreResult({ result, onPdf }) {
  const { isDark } = useTheme();
  if (!result) return null;

  const isAccorde = result.decision === "ACCORDE";
  const proba = Math.round(result.probabilite_defaut * 100 * 10) / 10; // en %, 1 décimale

  // Config du niveau de risque (nos 3 niveaux)
  const riskCfg = {
    faible: { text: isDark ? "text-emerald-400" : "text-emerald-700", border: isDark ? "border-emerald-800" : "border-emerald-200" },
    moyen: { text: isDark ? "text-amber-400" : "text-amber-700", border: isDark ? "border-amber-800" : "border-amber-200" },
    eleve: { text: isDark ? "text-red-400" : "text-red-700", border: isDark ? "border-red-800" : "border-red-200" },
  };
  const rc = riskCfg[result.classe_risque] || riskCfg.moyen;

  const decisionColor = isAccorde
    ? (isDark ? "text-emerald-400 border-emerald-800" : "text-emerald-700 border-emerald-200")
    : (isDark ? "text-red-400 border-red-800" : "text-red-700 border-red-200");

  return (
    <div className={"rounded-2xl border overflow-hidden animate-fadeUp " +
      (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm")}>
      <div className="p-5 lg:p-6">
        {/* Décision */}
        <div className={"flex items-center justify-center gap-2.5 py-4 rounded-xl border mb-4 font-bold text-xl " + decisionColor}>
          {isAccorde ? <CheckCircle size={24} /> : <XCircle size={24} />}
          {isAccorde ? "CRÉDIT ACCORDÉ" : "CRÉDIT REFUSÉ"}
        </div>

        {/* Speedometer */}
        <div className={"rounded-xl p-3 mb-4 " + (isDark ? "bg-zinc-800/40" : "bg-gray-50")}>
          <Speedometer proba={proba} isDark={isDark} />
        </div>

        {/* Légende des seuils */}
        <div className={"rounded-xl px-4 py-2.5 mb-4 flex items-center justify-around flex-wrap gap-2 " +
          (isDark ? "bg-zinc-800/40" : "bg-gray-50")}>
          {[
            { label: "Faible", color: "bg-emerald-500", range: "< 40%" },
            { label: "Moyen", color: "bg-amber-500", range: "40-70%" },
            { label: "Élevé", color: "bg-red-500", range: "> 70%" },
          ].map((z) => (
            <div key={z.label} className="flex items-center gap-1.5">
              <span className={"w-2 h-2 rounded-full " + z.color} />
              <span className={"text-xs " + (isDark ? "text-zinc-400" : "text-gray-500")}>
                {z.label} <span className={isDark ? "text-zinc-600" : "text-gray-400"}>({z.range})</span>
              </span>
            </div>
          ))}
        </div>

        {/* Niveau de risque */}
        <div className={"rounded-xl border px-4 py-3 mb-4 flex items-center justify-between " +
          (isDark ? "border-zinc-800" : "border-gray-100")}>
          <div>
            <p className={"text-xs uppercase tracking-wider mb-0.5 " + (isDark ? "text-zinc-500" : "text-gray-400")}>Niveau de risque</p>
            <p className={"font-bold text-base capitalize " + rc.text}>{result.classe_risque}</p>
          </div>
          <span className={"text-xs px-2.5 py-1 rounded-full border font-medium capitalize " + rc.text + " " + rc.border}>
            {result.classe_risque}
          </span>
        </div>

        {/* Explication en langage naturel */}
        {result.explication && (
          <div className={"rounded-xl p-3.5 mb-4 text-xs leading-relaxed " +
            (isDark ? "bg-zinc-800/40 text-zinc-300" : "bg-gray-50 text-gray-600")}>
            {result.explication}
          </div>
        )}

        {/* Barre de risque avec seuil */}
        <div className="mb-4">
          <div className="flex justify-between text-xs mb-1.5">
            <span className={isDark ? "text-zinc-500" : "text-gray-400"}>Risque de défaut</span>
            <span className={"font-medium " + getProbaColor(proba)}>{proba}%</span>
          </div>
          <div className={"relative w-full h-2 rounded-full " + (isDark ? "bg-zinc-800" : "bg-gray-100")}>
            <div className={"h-2 rounded-full transition-all duration-1000 " + getBarColor(proba)} style={{ width: proba + "%" }} />
            <div className="absolute top-0 h-2 w-0.5 bg-red-500 opacity-70" style={{ left: "70%" }} title="Seuil : 70%" />
          </div>
        </div>

        {/* Bouton PDF */}
        {onPdf && (
          <button onClick={onPdf}
            className={"w-full py-2.5 rounded-lg text-sm font-medium border transition flex items-center justify-center gap-2 " +
              (isDark ? "border-zinc-700 text-zinc-300 hover:bg-zinc-800" : "border-gray-200 text-gray-600 hover:bg-gray-50")}>
            <FileDown size={16} /> Exporter la fiche PDF
          </button>
        )}
      </div>
    </div>
  );
}
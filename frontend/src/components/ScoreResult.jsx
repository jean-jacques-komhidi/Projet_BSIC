import { useTheme } from "../context/ThemeContext";
import { CheckCircle, XCircle, FileDown } from "lucide-react";
import { useEffect, useState } from "react";

// Seuils adaptés à notre backend (3 niveaux, seuil décision 70%)
// < 40%  → faible → vert
// 40-70% → moyen  → ambre
// > 70%  → élevé  → rouge
// Couleurs de l'application : vert = faible, orange = moyen, rouge = eleve
const VERT = "#0F6E56", ORANGE = "#d97706", ROUGE = "#c0392b";
const getColor = (p) => {
  if (p < 40) return VERT;
  if (p < 70) return ORANGE;
  return ROUGE;
};
const LIBELLE_RISQUE = { faible: "Faible", moyen: "Moyen", eleve: "Élevé" };

// ── SPEEDOMETER ──
export function Speedometer({ proba, isDark }) {
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
    { from: 180, to: 180 - (40 / 100) * 180, color: VERT },
    { from: 180 - (40 / 100) * 180, to: 180 - (70 / 100) * 180, color: ORANGE },
    { from: 180 - (70 / 100) * 180, to: 0, color: ROUGE },
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
              <line x1={sx1} y1={sy1} x2={sx2} y2={sy2} stroke={ROUGE} strokeWidth="2" strokeDasharray="3,2" />
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
          style={{ transition: "fill 0.3s" }}>{animated.toFixed(1).replace(".", ",")} %</text>
        <text x={cx} y={cy + 54} textAnchor="middle" fontSize="9" fill={tickColor}>Probabilité de défaut</text>
      </svg>
    </div>
  );
}

// ── SCORE RESULT ──
// texte : explication a afficher (par defaut, celle renvoyee par l'analyse)
export default function ScoreResult({ result, onPdf, texte }) {
  const { isDark } = useTheme();
  if (!result) return null;

  const isAccorde = result.decision === "ACCORDE";
  const proba = Math.round(result.probabilite_defaut * 100 * 10) / 10; // en %, 1 décimale
  const couleurDecision = isAccorde ? VERT : ROUGE;
  const niveau = LIBELLE_RISQUE[result.classe_risque] || result.classe_risque;
  const explication = texte || result.explication;

  return (
    <div className={"rounded-2xl border overflow-hidden animate-fadeUp " +
      (isDark ? "bg-zinc-900 border-zinc-800" : "bg-white border-gray-100 shadow-sm")}>
      <div className="p-5 lg:p-6">
        {/* Décision et niveau de risque */}
        <div className="flex flex-col items-center justify-center gap-1 py-4 rounded-xl border mb-4"
          style={{ borderColor: couleurDecision + "55", backgroundColor: couleurDecision + (isDark ? "1f" : "0d") }}>
          <span className="flex items-center gap-2.5 font-bold text-xl"
            style={{ color: isDark ? (isAccorde ? "#34d399" : "#f87171") : couleurDecision }}>
            {isAccorde ? <CheckCircle size={24} /> : <XCircle size={24} />}
            {isAccorde ? "CRÉDIT ACCORDÉ" : "CRÉDIT REFUSÉ"}
          </span>
          <span className={"text-xs " + (isDark ? "text-zinc-400" : "text-gray-500")}>
            Risque {niveau ? niveau.toLowerCase() : "—"}, seuil de refus à 70 %
          </span>
        </div>

        {/* Jauge */}
        <div className={"rounded-xl p-3 mb-4 " + (isDark ? "bg-zinc-800/40" : "bg-gray-50")}>
          <Speedometer proba={proba} isDark={isDark} />
          <div className="flex items-center justify-center flex-wrap gap-x-5 gap-y-1 pt-1">
            {[
              { label: "Faible", color: VERT, range: "moins de 40 %" },
              { label: "Moyen", color: ORANGE, range: "40 à 70 %" },
              { label: "Élevé", color: ROUGE, range: "70 % et plus" },
            ].map((z) => (
              <span key={z.label} className={"flex items-center gap-1.5 text-xs " + (isDark ? "text-zinc-400" : "text-gray-500")}>
                <span className="w-2 h-2 rounded-full" style={{ background: z.color }} />
                {z.label} <span className={isDark ? "text-zinc-600" : "text-gray-400"}>({z.range})</span>
              </span>
            ))}
          </div>
        </div>

        {/* Explication en langage naturel */}
        {explication && (
          <div className={"rounded-xl p-3.5 text-xs leading-relaxed " + (onPdf ? "mb-4 " : "") +
            (isDark ? "bg-zinc-800/40 text-zinc-300" : "bg-gray-50 text-gray-600")}>
            {explication}
          </div>
        )}

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

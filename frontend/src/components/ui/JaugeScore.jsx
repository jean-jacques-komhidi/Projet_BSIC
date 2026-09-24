// Jauge de vitesse (demi-cercle) avec aiguille pointant le score
export default function JaugeScore({ score, isDark }) {
  // score = probabilité de défaut en % (0 à 100)
  // L'aiguille va de -90° (0%) à +90° (100%)
  const angle = -90 + (score / 100) * 180;

  // Couleur selon le score
  let couleur;
  if (score < 30) couleur = "#0F6E56";      // vert : faible risque
  else if (score < 70) couleur = "#d97706"; // orange : risque moyen
  else couleur = "#c0392b";                  // rouge : risque élevé

  const R = 90;      // rayon
  const cx = 110, cy = 110;

  // Créer les arcs colorés (3 zones)
  function arc(debut, fin, col) {
    const a1 = (-90 + debut * 1.8) * (Math.PI / 180);
    const a2 = (-90 + fin * 1.8) * (Math.PI / 180);
    const x1 = cx + R * Math.cos(a1), y1 = cy + R * Math.sin(a1);
    const x2 = cx + R * Math.cos(a2), y2 = cy + R * Math.sin(a2);
    const large = fin - debut > 50 ? 1 : 0;
    return `M ${x1} ${y1} A ${R} ${R} 0 ${large} 1 ${x2} ${y2}`;
  }

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 220 130" className="w-full max-w-60">
        {/* Zones colorées */}
        <path d={arc(0, 30)} fill="none" stroke="#0F6E56" strokeWidth="14" strokeLinecap="round" opacity="0.85" />
        <path d={arc(33, 67)} fill="none" stroke="#d97706" strokeWidth="14" strokeLinecap="round" opacity="0.85" />
        <path d={arc(70, 100)} fill="none" stroke="#c0392b" strokeWidth="14" strokeLinecap="round" opacity="0.85" />

        {/* Aiguille */}
        <line
          x1={cx} y1={cy}
          x2={cx + (R - 25) * Math.cos(angle * Math.PI / 180)}
          y2={cy + (R - 25) * Math.sin(angle * Math.PI / 180)}
          stroke={isDark ? "#ffffff" : "#1a1a1a"}
          strokeWidth="3" strokeLinecap="round"
          style={{ transition: "all 0.8s ease" }}
        />
        {/* Centre de l'aiguille */}
        <circle cx={cx} cy={cy} r="6" fill={couleur} />
      </svg>

      {/* Valeur */}
      <div className="text-center -mt-2">
        <p className="text-3xl font-bold" style={{ color: couleur }}>{score}%</p>
        <p className={"text-xs " + (isDark ? "text-zinc-500" : "text-gray-400")}>Probabilité de défaut</p>
      </div>
    </div>
  );
}
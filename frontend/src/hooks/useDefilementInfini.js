import { useState, useEffect, useRef, useCallback } from "react";

// Défilement infini : affiche `pas` lignes, puis les suivantes quand le bas
// de la liste devient visible (un repère est placé sous la dernière ligne).
// Renvoie [nombre de lignes à afficher, ref du repère, chargement en cours, réinitialiser].
export default function useDefilementInfini(total, pas = 20) {
  const [nombre, setNombre] = useState(pas);
  const [chargement, setChargement] = useState(false);
  const repere = useRef(null);

  useEffect(() => {
    const el = repere.current;
    if (!el || nombre >= total) return undefined;
    let minuterie;
    const observateur = new IntersectionObserver(([entree]) => {
      if (!entree.isIntersecting || minuterie) return;
      setChargement(true);
      // Court délai pour que l'arrivée des lignes suivantes soit perceptible
      minuterie = setTimeout(() => {
        setNombre((n) => Math.min(n + pas, total));
        setChargement(false);
        minuterie = null;
      }, 350);
    }, { rootMargin: "120px" });
    observateur.observe(el);
    return () => { observateur.disconnect(); clearTimeout(minuterie); };
  }, [nombre, total, pas]);

  const reinitialiser = useCallback(() => setNombre(pas), [pas]);
  return [Math.min(nombre, total), repere, chargement, reinitialiser];
}

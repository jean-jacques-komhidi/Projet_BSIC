import { createContext, useContext, useState, useEffect } from "react";

const ThemeContext = createContext();
const requeteSombre = "(prefers-color-scheme: dark)";

function lireMode() {
  try {
    const m = localStorage.getItem("theme");
    return m === "sombre" || m === "systeme" ? m : "clair";
  } catch {
    return "clair";
  }
}

function systemeSombre() {
  return typeof window !== "undefined" && window.matchMedia ? window.matchMedia(requeteSombre).matches : false;
}

// Thème : "clair", "sombre" ou "systeme" (suit le réglage de l'appareil)
export function ThemeProvider({ children }) {
  const [mode, setMode] = useState(lireMode);
  const [sombreSysteme, setSombreSysteme] = useState(systemeSombre);
  const sombre = mode === "sombre" || (mode === "systeme" && sombreSysteme);

  useEffect(() => {
    if (!window.matchMedia) return;
    const mq = window.matchMedia(requeteSombre);
    const suivre = (e) => setSombreSysteme(e.matches);
    mq.addEventListener("change", suivre);
    return () => mq.removeEventListener("change", suivre);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", sombre);
    try { localStorage.setItem("theme", mode); } catch { /* stockage indisponible */ }
  }, [sombre, mode]);

  function basculer() {
    setMode(sombre ? "clair" : "sombre");
  }

  return (
    <ThemeContext.Provider
      value={{ sombre, basculer, isDark: sombre, toggleTheme: basculer, mode, setMode }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}

import { createContext, useContext, useState, useEffect } from "react";

const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [sombre, setSombre] = useState(
    localStorage.getItem("theme") === "sombre"
  );

  useEffect(() => {
    if (sombre) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "sombre");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "clair");
    }
  }, [sombre]);

  function basculer() {
    setSombre((s) => !s);
  }

  return (
    <ThemeContext.Provider
      value={{ sombre, basculer, isDark: sombre, toggleTheme: basculer }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
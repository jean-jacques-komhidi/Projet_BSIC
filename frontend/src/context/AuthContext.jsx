import { createContext, useContext, useState, useEffect } from "react";
import { utilisateurCourant, seDeconnecter } from "../services/authService";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [utilisateur, setUtilisateur] = useState(null);
  const [chargement, setChargement] = useState(true);

  // Au démarrage, si un jeton existe, récupérer l'utilisateur
  useEffect(() => {
    async function verifier() {
      const token = localStorage.getItem("token");
      if (token) {
        try {
          const u = await utilisateurCourant();
          setUtilisateur(u);
        } catch {
          localStorage.removeItem("token");
        }
      }
      setChargement(false);
    }
    verifier();
  }, []);

  // Rafraîchir l'utilisateur après connexion
  async function rafraichir() {
    const u = await utilisateurCourant();
    setUtilisateur(u);
  }

  function deconnexion() {
    seDeconnecter();
    setUtilisateur(null);
  }

  return (
    <AuthContext.Provider value={{ utilisateur, chargement, rafraichir, deconnexion }}>
      {children}
    </AuthContext.Provider>
  );
}

// Hook pratique pour utiliser le context partout
export function useAuth() {
  return useContext(AuthContext);
}
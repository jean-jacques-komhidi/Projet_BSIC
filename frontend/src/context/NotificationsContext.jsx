import { createContext, useContext, useState, useEffect } from "react";
import { getNonLues } from "../services/notificationService";
import { useAuth } from "./AuthContext";

const NotificationsContext = createContext();

export function NotificationsProvider({ children }) {
  const { utilisateur } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);

  async function rafraichirCompteur() {
    if (!utilisateur) return;
    try {
      const n = await getNonLues();
      setUnreadCount(n);
    } catch {
      setUnreadCount(0);
    }
  }

  // Rafraîchir quand l'utilisateur change, puis toutes les 30 secondes
  useEffect(() => {
    rafraichirCompteur();
    const intervalle = setInterval(rafraichirCompteur, 30000);
    return () => clearInterval(intervalle);
  }, [utilisateur]);

  return (
    <NotificationsContext.Provider value={{ unreadCount, rafraichirCompteur }}>
      {children}
    </NotificationsContext.Provider>
  );
}

export function useNotifications() {
  return useContext(NotificationsContext);
}
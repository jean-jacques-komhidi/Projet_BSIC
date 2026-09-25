import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import ClientsPage from "./pages/ClientsPage";
import AnalysePage from "./pages/AnalysePage";
import HistoriquePage from "./pages/HistoriquePage";
import AnalyseDetailPage from "./pages/AnalyseDetailPage";
import AssistantPage from "./pages/AssistantPage";
import NotificationsPage from "./pages/NotificationsPage";
import UtilisateursPage from "./pages/UtilisateursPage";
import UtilisateurFormPage from "./pages/UtilisateurFormPage";
import SurveillancePage from "./pages/SurveillancePage";
import MonitoringPage from "./pages/MonitoringPage";
import ProfilPage from "./pages/ProfilPage";
import Layout from "./components/layout/Layout";

// Composant qui protège les pages : redirige vers /login si non connecté
function PageProtegee({ children }) {
  const { utilisateur, chargement } = useAuth();
  if (chargement) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p style={{ color: "var(--texte-secondaire)" }}>Chargement...</p>
      </div>
    );
  }
  if (!utilisateur) {
    return <Navigate to="/login" replace />;
  }
  return <Layout>{children}</Layout>;
}

function App() {
  const { utilisateur, rafraichir } = useAuth();

  return (
    <Routes>
      {/* Page de connexion */}
      <Route
        path="/login"
        element={
          utilisateur ? (
            <Navigate to="/tableau-de-bord" replace />
          ) : (
            <LoginPage
              onConnexionReussie={async () => {
                await rafraichir();
              }}
            />
          )
        }
      />

      {/* Pages protégées */}
      <Route
        path="/tableau-de-bord"
        element={
          <PageProtegee>
            <DashboardPage />
          </PageProtegee>
        }
      />
      <Route 
        path="/clients" 
        element={
          <PageProtegee>
            <ClientsPage />
          </PageProtegee>
        } />
        <Route 
          path="/analyse"
           element={
            <PageProtegee>
              <AnalysePage />
            </PageProtegee>
          } />
          <Route path="/historique" element={<PageProtegee><HistoriquePage /></PageProtegee>} />
          <Route path="/analyse/:id" element={<PageProtegee><AnalyseDetailPage /></PageProtegee>} />
          <Route path="/assistant" element={<PageProtegee><AssistantPage /></PageProtegee>} />
          <Route path="/notifications" element={<PageProtegee><NotificationsPage /></PageProtegee>} />
          <Route path="/utilisateurs" element={<PageProtegee><UtilisateursPage /></PageProtegee>} />
          <Route path="/utilisateurs/nouveau" element={<PageProtegee><UtilisateurFormPage /></PageProtegee>} />
          <Route path="/utilisateurs/:id/modifier" element={<PageProtegee><UtilisateurFormPage /></PageProtegee>} />
          <Route path="/surveillance" element={<PageProtegee><SurveillancePage /></PageProtegee>} />
          <Route path="/monitoring" element={<PageProtegee><MonitoringPage /></PageProtegee>} />
          <Route path="/profil" element={<PageProtegee><ProfilPage /></PageProtegee>} />

      {/* Redirection par défaut */}
      <Route path="*" element={<Navigate to="/tableau-de-bord" replace />} />
    </Routes>
  );
}

export default App;
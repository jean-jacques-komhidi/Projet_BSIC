import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import ClientsPage from "./pages/ClientsPage";
import AnalysePage from "./pages/AnalysePage";
import HistoriquePage from "./pages/HistoriquePage";
import AnalyseDetailPage from "./pages/AnalyseDetailPage";
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

      {/* Redirection par défaut */}
      <Route path="*" element={<Navigate to="/tableau-de-bord" replace />} />
    </Routes>
  );
}

export default App;
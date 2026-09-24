import Sidebar from "./Sidebar";

function Layout({ children }) {
  return (
    <div className="min-h-screen" style={{ backgroundColor: "var(--fond)" }}>
      <Sidebar />
      {/* Contenu principal : décalé à droite (sidebar) et sous le header fixe */}
      <main className="lg:ml-64 min-h-screen pt-16 lg:pt-20">
        <div className="p-4 lg:p-8">{children}</div>
      </main>
    </div>
  );
}

export default Layout;
import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { getSession } from "../services/auth";
import Sidebar from "./Sidebar";

export default function ProtectedRoute({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    getSession().then((s) => {
      setSession(s);
      setLoading(false);
    });
    const onKey = (e) => { if (e.key === "Escape") setSidebarOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  if (loading) return <div className="page-loader"><div className="spinner" /></div>;
  if (!session) return <Navigate to="/login" replace />;

  return (
    <div className="app-layout">
      <div className={`sidebar-overlay ${sidebarOpen ? "open" : ""}`} onClick={() => setSidebarOpen(false)} />
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <main className="main-content">
        <button className="menu-toggle" onClick={() => setSidebarOpen(true)}>
          &#9776;
        </button>
        {children}
      </main>
    </div>
  );
}

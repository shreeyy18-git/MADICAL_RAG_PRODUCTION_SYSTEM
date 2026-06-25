import { NavLink } from "react-router-dom";

const links = [
  { to: "/dashboard", label: "Dashboard", icon: "D" },
  { to: "/chat", label: "Chat", icon: "C" },
  { to: "/history", label: "History", icon: "H" },
  { to: "/profile", label: "Profile", icon: "P" },
];

export default function Sidebar({ open, onClose }) {
  return (
    <aside className={`sidebar${open ? " open" : ""}`}>
      <div className="sidebar-header">
        <span className="logo-icon">+</span>
        <span>Medical AI</span>
      </div>
      <nav className="sidebar-nav">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            className={({ isActive }) => `sidebar-link ${isActive ? "active" : ""}`}
            onClick={onClose}
          >
            <span className="sidebar-icon">{l.icon}</span>
            {l.label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <NavLink to="/login" className="sidebar-link logout" onClick={onClose}>
          <span className="sidebar-icon">X</span>
          Logout
        </NavLink>
      </div>
    </aside>
  );
}

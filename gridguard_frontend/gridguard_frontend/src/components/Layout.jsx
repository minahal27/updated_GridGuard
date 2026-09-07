import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useDatasets } from "../context/DatasetContext";
import { useTheme } from "../context/ThemeContext";
import BrandMark from "./BrandMark";
import { StatusBadge } from "./Common";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/filters", label: "Data Filters" },
  { to: "/datasets", label: "Datasets" },
  { to: "/anomalies", label: "Anomaly Results" },
  { to: "/feeders", label: "Network Loss" },
  { to: "/alerts", label: "Alerts" },
  { to: "/reports", label: "Reports" },
];

const ADMIN_NAV_ITEMS = [
  { to: "/models", label: "ML Models" },
  { to: "/thresholds", label: "Thresholds" },
  { to: "/logs", label: "System Logs" },
];

const ACCOUNT_NAV_ITEMS = [{ to: "/settings", label: "Settings" }];

function ThemeToggleButton() {
  const { theme, toggleTheme } = useTheme();
  return (
    <button
      type="button"
      className="theme-toggle-btn"
      onClick={toggleTheme}
      title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      aria-label="Toggle color theme"
    >
      {theme === "dark" ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="4.2" stroke="currentColor" strokeWidth="1.6" />
          <path
            d="M12 2.5V5M12 19V21.5M4.2 4.2L6 6M18 18L19.8 19.8M2.5 12H5M19 12H21.5M4.2 19.8L6 18M18 6L19.8 4.2"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path
            d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5Z"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </button>
  );
}

export default function Layout() {
  const { user, logout, isAdmin } = useAuth();
  const { datasets, activeDatasetId, setActiveDatasetId, activeDataset } = useDatasets();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const toggleMobileMenu = () => {
    setMobileMenuOpen(!mobileMenuOpen);
  };

  const closeMobileMenu = () => {
    setMobileMenuOpen(false);
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-main">
          <div className="brand" style={{ marginRight: '1rem' }}>
            <BrandMark />
            GridGuard
          </div>

          {/* Desktop Navigation */}
          <nav className="desktop-nav">
            <div className="top-nav-group">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          </nav>

          <div className="topbar-actions">
            <div className="flex items-center gap-3">
              <span className="text-sm text-dim">Dataset</span>
              <select
                className="select"
                value={activeDatasetId || ""}
                onChange={(e) => setActiveDatasetId(Number(e.target.value))}
                style={{ width: '120px', padding: '6px 10px' }}
              >
                {datasets.length === 0 && <option value="">No datasets uploaded</option>}
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.file_name} (#{d.id})
                  </option>
                ))}
              </select>
              {activeDataset && <StatusBadge status={activeDataset.status} />}
            </div>
            <div className="flex items-center gap-3" style={{ borderLeft: '1px solid var(--hairline)', paddingLeft: '1rem' }}>
              <ThemeToggleButton />
              <div className="dropdown-container">
                <button className="user-btn">
                  <span className="text-sm mono">{user?.name}</span>
                </button>
                <div className="dropdown-menu">
                  {isAdmin && ADMIN_NAV_ITEMS.map(item => (
                    <NavLink key={item.to} to={item.to} className="dropdown-item">{item.label}</NavLink>
                  ))}
                  {ACCOUNT_NAV_ITEMS.map(item => (
                    <NavLink key={item.to} to={item.to} className="dropdown-item">{item.label}</NavLink>
                  ))}
                  <div className="dropdown-divider"></div>
                  <button onClick={handleLogout} className="dropdown-item text-danger">Log out</button>
                </div>
              </div>
            </div>
          </div>

          <button className="mobile-menu-btn" onClick={toggleMobileMenu}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <nav className="mobile-nav">
            <div className="nav-group">
              <span className="nav-label">Monitoring</span>
              {NAV_ITEMS.map((item) => (
                <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`} onClick={closeMobileMenu}>
                  {item.label}
                </NavLink>
              ))}
            </div>
            
            {isAdmin && (
              <div className="nav-group">
                <span className="nav-label">Administration</span>
                {ADMIN_NAV_ITEMS.map((item) => (
                  <NavLink key={item.to} to={item.to} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`} onClick={closeMobileMenu}>
                    {item.label}
                  </NavLink>
                ))}
              </div>
            )}
            
            <div className="nav-group">
              <span className="nav-label">Account</span>
              {ACCOUNT_NAV_ITEMS.map((item) => (
                <NavLink key={item.to} to={item.to} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`} onClick={closeMobileMenu}>
                  {item.label}
                </NavLink>
              ))}
              <button className="nav-link" onClick={() => { handleLogout(); closeMobileMenu(); }} style={{ background: 'none', border: 'none', width: '100%', textAlign: 'left', cursor: 'pointer' }}>
                Log out
              </button>
            </div>
          </nav>
        )}
      </header>

      <main className="main-area">
        <div className="content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

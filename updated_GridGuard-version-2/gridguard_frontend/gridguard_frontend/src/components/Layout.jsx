import { useState, useEffect } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useDatasets } from "../context/DatasetContext";
import { useTheme } from "../context/ThemeContext";
import BrandMark from "./BrandMark";
import { StatusBadge } from "./Common";
import TheftDetectionBackground from "./TheftDetectionBackground";

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
  { to: "/users", label: "Users" },
];

const ACCOUNT_NAV_ITEMS = [{ to: "/settings", label: "Settings" }];

function ThemeToggleButton() {
  const { theme, toggleTheme } = useTheme();
  return (
    <button
      type="button"
      className="theme-toggle-btn"
      onClick={toggleTheme}
      title={theme === "dark" ? "Switch to Liquid Light (White & Red)" : "Switch to Liquid Dark (Blue & Red)"}
      aria-label="Toggle color theme"
    >
      {theme === "dark" ? (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="4.2" stroke="currentColor" strokeWidth="2" />
          <path
            d="M12 2.5V5M12 19V21.5M4.2 4.2L6 6M18 18L19.8 19.8M2.5 12H5M19 12H21.5M4.2 19.8L6 18M18 6L19.8 4.2"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      ) : (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path
            d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5Z"
            stroke="currentColor"
            strokeWidth="2"
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
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Quick Cinematic Backdrop Flash on Page Switch (less than a second)
  const [pageTransitioning, setPageTransitioning] = useState(false);
  const [revealedLocation, setRevealedLocation] = useState(location.pathname);

  useEffect(() => {
    if (location.pathname !== revealedLocation) {
      setPageTransitioning(true);
      // Fast, snappy 600ms reveal so the transition feels responsive and sleek
      const timer = setTimeout(() => {
        setRevealedLocation(location.pathname);
        setPageTransitioning(false);
      }, 600);
      return () => clearTimeout(timer);
    }
  }, [location.pathname, revealedLocation]);

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
    <div className={`app-shell ${pageTransitioning ? "scada-transition-active" : ""}`}>
      {/* Dynamic Cybernetic Liquid Smart Grid Background Canvas */}
      <div className="liquid-bg-viewport">
        <TheftDetectionBackground />
        <div className="liquid-radial-glow top-left"></div>
        <div className="liquid-radial-glow top-right"></div>
        <div className="liquid-radial-glow bottom-center"></div>
      </div>

      <header className="topbar">
        <div className="topbar-main">
          <div className="brand" onClick={() => navigate("/")} style={{ cursor: "pointer" }}>
            <div className="brand-glow-wrap">
              <BrandMark size={28} />
            </div>
            <span className="brand-text">
              Grid<span className="brand-accent">Guard</span>
            </span>
            <span className="brand-pill">SCADA 2.4</span>
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
            <div className="dataset-selector-glass">
              <div className="dataset-dot"></div>
              <span className="text-xs text-dim uppercase tracking-wider font-semibold">FEED</span>
              <select
                className="select-glass-nav"
                value={activeDatasetId || ""}
                onChange={(e) => setActiveDatasetId(Number(e.target.value))}
              >
                {datasets.length === 0 && <option value="">No dataset uploaded</option>}
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.file_name} (#{d.id})
                  </option>
                ))}
              </select>
              {activeDataset && <StatusBadge status={activeDataset.status} />}
            </div>

            <div className="topbar-divider"></div>

            <ThemeToggleButton />

            <div className="dropdown-container">
              <button className="user-btn">
                <span className="user-avatar-dot"></span>
                <span className="text-sm mono font-semibold">{user?.name || "Operator"}</span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>
              <div className="dropdown-menu">
                <div className="dropdown-header">
                  <span className="dropdown-role">{isAdmin ? "SYSTEM ADMINISTRATOR" : "ANALYST"}</span>
                  <span className="dropdown-email">{user?.email}</span>
                </div>
                <div className="dropdown-divider"></div>
                {isAdmin && ADMIN_NAV_ITEMS.map((item) => (
                  <NavLink key={item.to} to={item.to} className="dropdown-item">
                    {item.label}
                  </NavLink>
                ))}
                {ACCOUNT_NAV_ITEMS.map((item) => (
                  <NavLink key={item.to} to={item.to} className="dropdown-item">
                    {item.label}
                  </NavLink>
                ))}
                <div className="dropdown-divider"></div>
                <button onClick={handleLogout} className="dropdown-item text-danger">
                  Log out
                </button>
              </div>
            </div>
          </div>

          <button className="mobile-menu-btn" onClick={toggleMobileMenu} aria-label="Open menu">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
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

      {/* Snappy Backdrop Reveal Transition HUD */}
      {pageTransitioning && (
        <div className="scada-reveal-overlay">
          <div className="scada-reveal-hud">
            <div className="scada-telemetry-badge">
              <span className="dataset-dot"></span>
              <span>SYNCHRONIZING TELEMETRY GRID</span>
            </div>
            <div className="scada-progress-container">
              <div className="scada-progress-bar"></div>
            </div>
            <span className="scada-live-status">LIVE TELEMETRY STREAM</span>
          </div>
        </div>
      )}

      <main className="main-area">
        <div className={`content ${pageTransitioning ? "content-hidden" : "content-fade-in"}`}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}

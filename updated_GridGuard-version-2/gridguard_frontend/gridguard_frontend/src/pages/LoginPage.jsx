import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import BrandMark from "../components/BrandMark";
import TheftDetectionBackground from "../components/TheftDetectionBackground";
import { Banner } from "../components/Common";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const from = location.state?.from?.pathname || "/";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || "Invalid email or password");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-shell">
      {/* Live Cyber Smart Grid Background Layer */}
      <TheftDetectionBackground />

      {/* Floating Liquid Lighting Spheres */}
      <div className="liquid-radial-glow top-left" />
      <div className="liquid-radial-glow top-right" />

      <div className="wireframe-login-container">
        <form className="wireframe-login-box" onSubmit={handleSubmit}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginBottom: "16px", gap: "10px" }}>
            <div className="brand-glow-wrap" style={{ padding: "10px" }}>
              <BrandMark size={40} />
            </div>
            <div style={{ textAlign: "center" }}>
              <span style={{ fontFamily: "var(--font-display)", fontSize: "28px", fontWeight: 800, letterSpacing: "-0.03em" }}>
                Grid<span style={{ background: "linear-gradient(135deg, var(--blue-liquid), var(--red-liquid))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Guard</span>
              </span>
              <div style={{ fontSize: "13px", color: "var(--text-mid)", fontWeight: 500, marginTop: "4px" }}>
                Next-Gen Electricity Theft Detection Console
              </div>
            </div>
          </div>

          <hr className="wireframe-divider" />
          
          {error && <Banner type="error">{error}</Banner>}

          <div className="wireframe-field">
            <label htmlFor="email">Operator ID or Email</label>
            <input
              id="email"
              className="wireframe-input"
              type="text"
              placeholder="operator@gridguard.scada"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="wireframe-field">
            <label htmlFor="password">Security Password</label>
            <input
              id="password"
              className="wireframe-input"
              type="password"
              placeholder="••••••••••••"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <div className="wireframe-action">
            <button className="wireframe-btn" type="submit" disabled={submitting}>
              {submitting ? "Verifying Credentials..." : "Authenticate & Connect"}
            </button>
          </div>
          
          <div className="wireframe-footer">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
              <span className="dataset-dot"></span>
              <span style={{ fontSize: "12px", color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}>
                ACTIVE TELEMETRY &middot; ML ENGINE ONLINE
              </span>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

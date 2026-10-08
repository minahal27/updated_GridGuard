import { useNavigate } from "react-router-dom";
import TheftDetectionBackground from "../components/TheftDetectionBackground";
import BrandMark from "../components/BrandMark";

export default function SplashPage() {
  const navigate = useNavigate();

  return (
    <div className="splash-layout">
      {/* Dynamic Cyber Smart Grid Background */}
      <TheftDetectionBackground />

      <div className="liquid-radial-glow top-left" />
      <div className="liquid-radial-glow top-right" />
      <div className="liquid-radial-glow bottom-center" />

      <div className="splash-content-transparent">
        <div className="splash-logo-center">
          <div className="brand-glow-wrap" style={{ padding: "10px" }}>
            <BrandMark size={40} />
          </div>
          <span className="splash-logo-text">GridGuard</span>
        </div>

        <h1 className="splash-hero-title">
          Smart Electricity Theft Detection System<br />
          <span className="splash-hero-highlight">INTELLIGENT GRID DEFENSE.</span>
        </h1>

        <h2 className="splash-subtitle">
          Real-time high-voltage telemetry & machine learning anomaly detection.
        </h2>

        <p className="splash-desc-transparent">
          Protect transmission networks with automated loss calculation, tamper recognition, and live executive briefs engineered for smart utility grids.
        </p>

        <div style={{ display: "flex", gap: "16px", justifyContent: "center", flexWrap: "wrap" }}>
          <button
            className="splash-hero-btn"
            onClick={() => navigate("/login")}
          >
            LAUNCH CONSOLE &rarr;
          </button>
        </div>
      </div>
    </div>
  );
}

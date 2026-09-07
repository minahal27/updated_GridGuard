import { useNavigate } from "react-router-dom";
import GridIllustration from "../components/GridIllustration";
import BrandMark from "../components/BrandMark";

export default function SplashPage() {
  const navigate = useNavigate();

  return (
    <div className="splash-layout">
      <div className="splash-visual">
        <GridIllustration />
      </div>

      <div className="splash-content-transparent">
        <div className="splash-logo-center">
          <BrandMark size={48} />
          <span className="splash-logo-text">GridGuard</span>
        </div>

        <h1 className="splash-hero-title">
          Smart Electricity Theft Detection System<br />
          <span className="splash-hero-highlight">REAL-TIME SECURITY.</span>
        </h1>

        <h2 className="splash-subtitle">
          Real-time transmission network analysis for security and integrity.
        </h2>

        <p className="splash-desc-transparent">
          Transform complex consumption history into professional executive briefs with precision-engineered machine learning.
        </p>

        <button
          className="splash-hero-btn"
          onClick={() => navigate("/login")}
        >
          CONTINUE &rarr;
        </button>
      </div>
    </div>
  );
}

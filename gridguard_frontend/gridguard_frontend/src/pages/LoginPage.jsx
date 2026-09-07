import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import BrandMark from "../components/BrandMark";
import GridIllustration from "../components/GridIllustration";
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
      <div className="auth-visual-background">
        <GridIllustration />
      </div>

      <div className="wireframe-login-container">
        <form className="wireframe-login-box" onSubmit={handleSubmit}>
          <h1 className="wireframe-title">Grid Guard: Smart Electricity Theft Detection System</h1>
          <hr className="wireframe-divider" />
          
          {error && <Banner type="error">{error}</Banner>}

          <div className="wireframe-field">
            <label htmlFor="email">Username or Email.</label>
            <input
              id="email"
              className="wireframe-input"
              type="text"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="wireframe-field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              className="wireframe-input"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <div className="wireframe-action">
            <button className="wireframe-btn" type="submit" disabled={submitting}>
              {submitting ? "Login..." : "Login"}
            </button>
          </div>
          
          <div className="wireframe-footer">
            <a href="#" className="wireframe-link">Forgot Password?</a>
          </div>
        </form>
      </div>
    </div>
  );
}

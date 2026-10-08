import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { api } from "../api/client";
import { Banner } from "../components/Common";

const THEME_OPTIONS = [
  { value: "dark", label: "Liquid Dark", blurb: "Liquid Blue & Electric Red glass with glowing telemetry depth." },
  { value: "light", label: "Liquid Light", blurb: "Liquid White & Crimson Red crystalline glass with specular sheen." },
];

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState(""); const [newPassword, setNewPassword] = useState(""); const [message, setMessage] = useState(""); const [error, setError] = useState("");
  const changePassword = async (e) => { e.preventDefault(); setError(""); setMessage(""); try { const r = await api.changePassword({ current_password: currentPassword, new_password: newPassword }); setMessage(r.detail); setCurrentPassword(""); setNewPassword(""); } catch (err) { setError(err.message); } };

  return (
    <div className="flex-col gap-5">
      <div>
        <h2>Settings</h2>
        <p className="mt-2">Preferences for this browser &mdash; signed in as {user?.name}.</p>
      </div>

      <div className="panel panel-pad"><h3>Security</h3><p className="text-sm text-dim mt-2">Change the initial password before presenting or deploying GridGuard.</p>{error && <Banner type="error">{error}</Banner>}{message && <Banner type="info">{message}</Banner>}<form className="flex items-end gap-3 mt-4" style={{ flexWrap: "wrap" }} onSubmit={changePassword}><div className="field"><label>Current password</label><input required type="password" className="input" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} /></div><div className="field"><label>New password (8+ characters)</label><input required minLength="8" type="password" className="input" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} /></div><button className="btn btn-primary">Change password</button></form></div>

      <div className="panel">
        <div className="panel-header">
          <h3>Appearance</h3>
        </div>
        <div className="panel-pad">
          <p className="text-sm text-dim mt-2" style={{ marginBottom: "var(--sp-4)" }}>
            Choose how GridGuard looks on this device. This is saved locally and doesn&rsquo;t affect other users.
          </p>
          <div className="theme-option-grid">
            {THEME_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`theme-option${theme === opt.value ? " active" : ""}`}
                onClick={() => setTheme(opt.value)}
              >
                <span className={`theme-swatch theme-swatch-${opt.value}`} aria-hidden="true">
                  <span className="theme-swatch-panel" />
                  <span className="theme-swatch-accent" />
                </span>
                <span className="flex-col" style={{ gap: 2 }}>
                  <span className="flex items-center gap-2">
                    <strong>{opt.label}</strong>
                    {theme === opt.value && <span className="badge badge-low">Active</span>}
                  </span>
                  <span className="text-sm text-dim">{opt.blurb}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

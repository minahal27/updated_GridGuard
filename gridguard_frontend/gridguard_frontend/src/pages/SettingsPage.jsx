import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

const THEME_OPTIONS = [
  { value: "dark", label: "Dark", blurb: "Substation-at-night palette. Easiest on the eyes in low light." },
  { value: "light", label: "Light", blurb: "Bright control-room palette. Better for well-lit rooms and printing reports." },
];

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { user } = useAuth();

  return (
    <div className="flex-col gap-5">
      <div>
        <h2>Settings</h2>
        <p className="mt-2">Preferences for this browser &mdash; signed in as {user?.name}.</p>
      </div>

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

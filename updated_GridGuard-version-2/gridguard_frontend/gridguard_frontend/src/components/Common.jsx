export function RiskBadge({ category }) {
  const cls = { High: "badge-high", Medium: "badge-medium", Low: "badge-low" }[category] || "badge-neutral";
  return <span className={`badge ${cls}`}>{category}</span>;
}

export function StatusBadge({ status }) {
  const map = {
    completed: "badge-low",
    processing: "badge-medium",
    uploaded: "badge-neutral",
    failed: "badge-high",
    New: "badge-high",
    Reviewed: "badge-medium",
    Resolved: "badge-low",
  };
  return <span className={`badge ${map[status] || "badge-neutral"}`}>{status}</span>;
}

/* GridPulse - signature liquid loading sweep with glowing telemetry trace */
export function GridPulse({ label = "Processing" }) {
  return (
    <div className="flex-col items-center gap-3" style={{ padding: "var(--sp-6) 0" }}>
      <div className="pulse-track">
        <div className="pulse-sweep" />
      </div>
      <span className="text-sm text-dim mono font-semibold tracking-wider uppercase">{label}&hellip;</span>
    </div>
  );
}

export function StatCard({ label, value, accent }) {
  const icons = {
    high: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    ),
    medium: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
    ),
    low: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <polyline points="22 4 12 14.01 9 11.01" />
      </svg>
    ),
    copper: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
    ),
  };

  const defaultIcon = (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );

  return (
    <div className={`stat-card ${accent ? `accent-${accent}` : ""}`}>
      <div className="stat-card-header">
        <span className="stat-label">{label}</span>
        <div className="stat-icon-wrap">
          {icons[accent] || defaultIcon}
        </div>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-card-glow-reflection"></div>
    </div>
  );
}

export function EmptyState({ title, body, action }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <h4>{title}</h4>
      {body && <p>{body}</p>}
      {action && <div className="empty-state-action">{action}</div>}
    </div>
  );
}

export function Banner({ type = "error", children }) {
  return (
    <div className={`banner banner-${type}`}>
      <div className="banner-icon">
        {type === "error" ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
        )}
      </div>
      <div className="banner-text">{children}</div>
    </div>
  );
}

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

/* GridPulse - the signature loading motif, a sweeping telemetry line. Used
   whenever the system is actively processing (upload analysis, retraining). */
export function GridPulse({ label = "Processing" }) {
  return (
    <div className="flex-col items-center gap-3" style={{ padding: "var(--sp-6) 0" }}>
      <div className="pulse-track">
        <div className="pulse-sweep" />
      </div>
      <span className="text-sm text-dim mono">{label}&hellip;</span>
    </div>
  );
}

export function StatCard({ label, value, accent }) {
  return (
    <div className={`stat-card ${accent ? `accent-${accent}` : ""}`}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}

export function EmptyState({ title, body, action }) {
  return (
    <div className="empty-state">
      <h4>{title}</h4>
      {body && <p>{body}</p>}
      {action}
    </div>
  );
}

export function Banner({ type = "error", children }) {
  return <div className={`banner banner-${type}`}>{children}</div>;
}

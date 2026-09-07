import { useEffect, useState } from "react";
import { api } from "../api/client";
import { EmptyState, GridPulse, Banner } from "../components/Common";
import { formatDateTime } from "../utils/datetime";

export default function LogsPage() {
  const [logs, setLogs] = useState([]);
  const [severity, setSeverity] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    api
      .listLogs({ severity: severity || undefined, limit: 200 })
      .then(setLogs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, [severity]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex-col gap-5">
      <div className="flex items-center justify-between">
        <div>
          <h2>System logs</h2>
          <p className="mt-2">Audit trail of uploads, logins, retraining, threshold changes, and errors.</p>
        </div>
        <select className="select" value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="">All severities</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
        </select>
      </div>

      {error && <Banner type="error">{error}</Banner>}

      <div className="panel">
        {loading ? (
          <GridPulse label="Loading logs" />
        ) : logs.length === 0 ? (
          <EmptyState title="No log entries" body="System events will appear here as they happen." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Details</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((l) => (
                  <tr key={l.id}>
                    <td className="mono">{l.event_type}</td>
                    <td>
                      <span className={`badge ${{ error: "badge-high", warning: "badge-medium", info: "badge-neutral" }[l.severity]}`}>
                        {l.severity}
                      </span>
                    </td>
                    <td className="text-sm text-mid">{l.status}</td>
                    <td className="text-sm text-mid">{l.details || "—"}</td>
                    <td className="text-sm text-dim mono">{formatDateTime(l.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

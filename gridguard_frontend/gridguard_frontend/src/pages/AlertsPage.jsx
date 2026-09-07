import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useDatasets } from "../context/DatasetContext";
import { api } from "../api/client";
import { RiskBadge, StatusBadge, EmptyState, GridPulse, Banner } from "../components/Common";
import { formatDateTime } from "../utils/datetime";

const TABS = ["Unresolved", "Reviewed"];

export default function AlertsPage() {
  const { activeDatasetId } = useDatasets();
  const [tab, setTab] = useState("Unresolved");
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [updatingId, setUpdatingId] = useState(null);
  
  // Modal State
  const [selectedAlert, setSelectedAlert] = useState(null);

  const load = () => {
    if (!activeDatasetId) return;
    setLoading(true);
    setError("");
    const apiStatus = tab === "Unresolved" ? "New" : tab;
    
    api
      .listAlerts({ dataset_id: activeDatasetId, status: apiStatus })
      .then(setAlerts)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [activeDatasetId, tab]);

  const handleUpdate = async (alertId, status) => {
    setUpdatingId(alertId);
    try {
      await api.updateAlert(alertId, status);
      // Remove from list if status no longer matches current tab's expected status
      const expectedApiStatus = tab === "Unresolved" ? "New" : tab;
      if (status !== expectedApiStatus) {
        setAlerts((prev) => prev.filter((a) => a.id !== alertId));
      } else {
        // Just update it locally
        setAlerts((prev) => prev.map(a => a.id === alertId ? { ...a, status } : a));
      }
      
      // Close modal if resolving from modal
      if (selectedAlert && selectedAlert.id === alertId) {
        setSelectedAlert(null);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setUpdatingId(null);
    }
  };

  const handleResolveAll = async () => {
    if (alerts.length === 0) return;
    setLoading(true);
    try {
      // Resolve all visible alerts
      await Promise.all(alerts.map(a => api.updateAlert(a.id, "Resolved")));
      setAlerts([]); // Clear the list since they are all resolved
    } catch(e) {
      setError("Failed to resolve all alerts.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-col gap-5 relative">
      <div>
        <h2>Alerts</h2>
      </div>

      <div className="flex gap-0" style={{ borderBottom: '1px solid var(--hairline)' }}>
        {TABS.map((t) => (
          <button
            key={t}
            className={`btn btn-sm ${tab === t ? "btn-primary" : "btn-ghost"}`}
            style={{ 
              borderRadius: 0, 
              border: '1px solid var(--hairline)', 
              borderBottom: tab === t ? 'none' : '1px solid var(--hairline)',
              backgroundColor: tab === t ? 'var(--bg-panel)' : 'transparent',
              color: tab === t ? 'var(--text-hi)' : 'var(--text-mid)',
              padding: '8px 16px'
            }}
            onClick={() => setTab(t)}
          >
            {t} {t === "Unresolved" ? `(${alerts.length})` : ""}
          </button>
        ))}
      </div>

      {error && <Banner type="error">{error}</Banner>}

      <div className="panel">
        {loading ? (
          <GridPulse label="Loading alerts" />
        ) : alerts.length === 0 ? (
          <EmptyState title={`No ${tab.toLowerCase()} alerts`} body="Alerts are generated automatically once a dataset finishes processing." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Consumer ID</th>
                  <th>Description</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((a) => (
                  <tr key={a.id}>
                    <td className="text-sm text-dim mono" style={{ whiteSpace: 'pre-line' }}>
                      {formatDateTime(a.created_at).replace(" ", "\n")}
                    </td>
                    <td>{a.cons_no}</td>
                    <td className="text-mid">{a.message}</td>
                    <td>
                      <RiskBadge category={a.severity} />
                    </td>
                    <td>
                       <span style={{ color: a.status === "New" ? "inherit" : "var(--text-dim)" }}>
                          {a.status === "New" ? "Unresolved" : a.status}
                       </span>
                    </td>
                    <td>
                      <div className="flex gap-2">
                        <button
                          className="btn btn-ghost btn-sm"
                          onClick={() => setSelectedAlert(a)}
                          style={{ border: '1px solid var(--hairline)' }}
                        >
                          Review
                        </button>
                        {a.status !== "Resolved" && (
                          <button
                            className="btn btn-ghost btn-sm"
                            disabled={updatingId === a.id}
                            onClick={() => handleUpdate(a.id, "Resolved")}
                            style={{ border: '1px solid var(--hairline)' }}
                          >
                            Resolve
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {alerts.length > 0 && tab === "Unresolved" && (
        <div style={{ marginTop: 8 }}>
          <button 
            className="btn btn-ghost btn-sm" 
            style={{ border: '1px solid var(--hairline)', padding: '6px 16px' }} 
            onClick={handleResolveAll} 
            disabled={loading}
          >
            Resolve All
          </button>
        </div>
      )}

      {/* Modal */}
      {selectedAlert && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ width: 450 }}>
            <div className="flex items-center justify-between" style={{ borderBottom: '1px solid var(--hairline)', paddingBottom: 16, marginBottom: 16 }}>
              <h3 style={{ fontSize: 18, color: 'var(--text-hi)', fontWeight: 600 }}>Alert Details</h3>
              <button 
                className="btn btn-ghost btn-sm" 
                onClick={() => setSelectedAlert(null)}
                style={{ fontSize: 16, padding: '4px 8px' }}
              >
                ✕
              </button>
            </div>
            
            <div className="flex-col gap-3 text-sm text-mid" style={{ marginBottom: 24 }}>
              <div><span className="text-hi" style={{ width: 100, display: 'inline-block' }}>Consumer ID:</span> {selectedAlert.cons_no}</div>
              <div><span className="text-hi" style={{ width: 100, display: 'inline-block' }}>Time:</span> {formatDateTime(selectedAlert.created_at)}</div>
              
              <div style={{ marginTop: 12, paddingBottom: 16, borderBottom: '1px dashed var(--hairline)' }}>
                <span className="text-hi" style={{ display: 'block', marginBottom: 8 }}>Description:</span> 
                {selectedAlert.message}
              </div>
              
              <div className="flex items-center gap-6 mt-3">
                <div className="flex items-center gap-3">
                  <span className="text-hi">Severity:</span>
                  <RiskBadge category={selectedAlert.severity} />
                </div>
                <div>
                  <span className="text-hi" style={{ marginRight: 8 }}>Status:</span> 
                  {selectedAlert.status === "New" ? "Unresolved" : selectedAlert.status}
                </div>
              </div>
            </div>

            <div className="flex gap-3 justify-end" style={{ borderTop: '1px solid var(--hairline)', paddingTop: 16 }}>
              {selectedAlert.status !== "Resolved" && (
                <button 
                  className="btn btn-primary btn-sm" 
                  disabled={updatingId === selectedAlert.id}
                  onClick={() => handleUpdate(selectedAlert.id, "Resolved")}
                  style={{ padding: '8px 16px' }}
                >
                  Mark Resolved
                </button>
              )}
              <button 
                className="btn btn-ghost btn-sm" 
                style={{ border: '1px solid var(--hairline)', padding: '8px 16px' }} 
                onClick={() => setSelectedAlert(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

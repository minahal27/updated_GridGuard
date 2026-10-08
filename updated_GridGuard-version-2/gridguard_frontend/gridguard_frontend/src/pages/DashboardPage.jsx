import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useDatasets } from "../context/DatasetContext";
import { api } from "../api/client";
import { StatCard, EmptyState, GridPulse, Banner } from "../components/Common";
import { formatDateTime } from "../utils/datetime";
import { RiskBadge } from "../components/Common";
import RiskDistributionChart from "../components/RiskDistributionChart";
import NetworkTrendChart from "../components/NetworkTrendChart";
import RiskHistogramChart from "../components/RiskHistogramChart";
import TopRiskConsumersChart from "../components/TopRiskConsumersChart";

export default function DashboardPage() {
  const { activeDataset, activeDatasetId, datasets, loading: datasetsLoading } = useDatasets();
  const [summary, setSummary] = useState(null);
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [trend, setTrend] = useState(null);
  const [histogram, setHistogram] = useState(null);
  const [topRisk, setTopRisk] = useState([]);
  const [feederSummary, setFeederSummary] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    if (!activeDatasetId || activeDataset?.status !== "completed") {
      setSummary(null);
      return;
    }
    setLoading(true);
    setError("");
    Promise.all([
      api.getDashboard(activeDatasetId),
      api.listAlerts({ dataset_id: activeDatasetId, status: "New" }),
      api.getNetworkTrend(activeDatasetId).catch(() => null),
      api.getRiskHistogram(activeDatasetId).catch(() => null),
      api.listAnomalies(activeDatasetId, { sort_by: "risk_score", page: 1, page_size: 8 }).catch(() => null),
      api.getFeederSummary(activeDatasetId).catch(() => null),
    ])
      .then(([s, alerts, trendData, histData, anomalies, feeders]) => {
        setSummary(s);
        setRecentAlerts(alerts.slice(0, 6));
        setTrend(trendData);
        setHistogram(histData);
        setTopRisk(anomalies ? anomalies.items : []);
        setFeederSummary(feeders);
        setLastUpdated(new Date());
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [activeDatasetId, activeDataset?.status, refreshKey]);

  useEffect(() => { if (!autoRefresh || !activeDatasetId || activeDataset?.status !== "completed") return; const timer = setInterval(() => setRefreshKey(k => k + 1), 30000); return () => clearInterval(timer); }, [autoRefresh, activeDatasetId, activeDataset?.status]);

  if (datasetsLoading) {
    return <GridPulse label="Loading datasets" />;
  }

  if (datasets.length === 0) {
    return (
      <EmptyState
        title="No datasets yet"
        body="Upload an electricity consumption dataset to start detecting anomalies."
        action={
          <Link className="btn btn-primary" to="/datasets">
            Upload a dataset
          </Link>
        }
      />
    );
  }

  if (activeDataset?.status === "processing" || activeDataset?.status === "uploaded") {
    return (
      <div className="panel panel-pad">
        <GridPulse label={`Analyzing ${activeDataset.file_name}`} />
        <p className="text-sm text-dim" style={{ textAlign: "center" }}>
          Preprocessing, feature engineering, and model training run in the background &mdash;
          this can take 30-60 seconds for large datasets.
        </p>
      </div>
    );
  }

  if (activeDataset?.status === "failed") {
    return <Banner type="error">Processing failed: {activeDataset.error_message}</Banner>;
  }

  if (error) return <Banner type="error">{error}</Banner>;
  if (loading || !summary) return <GridPulse label="Loading dashboard" />;

  return (
    <div className="flex-col gap-5">
      <div className="flex items-start justify-between gap-3" style={{ flexWrap: "wrap" }}>
        <div>
        <h2>Dashboard</h2>
        <p className="mt-2">
          {activeDataset.file_name} &middot; {summary.total_consumers.toLocaleString()} consumers analyzed
          {summary.active_model && (
            <>
              {" "}
              &middot; model <span className="mono">{summary.active_model}</span>
            </>
          )}
        </p>
        </div>
        <div className="flex items-center gap-2"><span className="text-sm text-dim">{lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : ""}</span><button className="btn btn-ghost btn-sm" onClick={() => setAutoRefresh(v => !v)}>{autoRefresh ? "Auto-refresh on" : "Auto-refresh off"}</button><button className="btn btn-primary btn-sm" onClick={() => setRefreshKey(k => k + 1)} disabled={loading}>Refresh</button></div>
      </div>

      <div className="stat-grid">
        <StatCard label="Total consumers" value={summary.total_consumers.toLocaleString()} />
        <StatCard label="High risk" value={summary.high_risk_count.toLocaleString()} accent="high" />
        <StatCard label="Medium risk" value={summary.medium_risk_count.toLocaleString()} accent="medium" />
        <StatCard label="Unresolved alerts" value={summary.unresolved_alerts.toLocaleString()} accent="copper" />
      </div>

      <div className="dash-chart-grid">
        <div className="panel">
          <div className="panel-header">
            <h3>Risk distribution</h3>
          </div>
          <div className="panel-pad">
            <RiskDistributionChart
              high={summary.high_risk_count}
              medium={summary.medium_risk_count}
              low={summary.low_risk_count}
            />
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h3>Risk score distribution</h3>
          </div>
          <div className="panel-pad">
            {histogram ? <RiskHistogramChart bins={histogram.bins} /> : <span className="text-sm text-dim">Not available</span>}
          </div>
        </div>
      </div>

      {feederSummary && (
        <div className="panel">
          <div className="panel-header">
            <h3>Network-wide loss (feeders)</h3>
            <Link to="/feeders" className="text-sm">
              View feeders &rarr;
            </Link>
          </div>
          <div className="panel-pad flex items-center gap-5" style={{ flexWrap: "wrap" }}>
            <div className="flex-col" style={{ gap: 2 }}>
              <span className="text-sm text-dim">Estimated network loss</span>
              <span className="mono" style={{ fontSize: 26, fontWeight: 700, color: "var(--risk-high)" }}>
                {feederSummary.overall_loss_pct.toFixed(1)}%
              </span>
            </div>
            <div className="flex-col" style={{ gap: 2 }}>
              <span className="text-sm text-dim">High-risk feeders</span>
              <span className="mono" style={{ fontSize: 26, fontWeight: 700 }}>
                {feederSummary.high_risk_feeders} / {feederSummary.feeder_count}
              </span>
            </div>
            {feederSummary.is_synthetic && (
              <span className="text-sm text-dim" style={{ maxWidth: 320 }}>
                Feeders auto-grouped &mdash; source file has no feeder/area column.
              </span>
            )}
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel-header">
          <h3>Network consumption trend</h3>
          {trend?.sampled && <span className="text-sm text-dim">downsampled for display</span>}
        </div>
        <div className="panel-pad" style={{ height: 260 }}>
          {trend ? (
            <NetworkTrendChart dates={trend.dates} values={trend.avg_consumption} />
          ) : (
            <span className="text-sm text-dim">Not available</span>
          )}
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h3>Top high-risk consumers</h3>
          <Link to="/anomalies" className="text-sm">
            View all &rarr;
          </Link>
        </div>
        <div className="panel-pad" style={{ height: 280 }}>
          {topRisk.length === 0 ? (
            <EmptyState title="No results yet" body="Risk scores will appear here once anomaly detection has run." />
          ) : (
            <TopRiskConsumersChart data={topRisk} />
          )}
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h3>Recent alerts</h3>
          <Link to="/alerts" className="text-sm">
            View all &rarr;
          </Link>
        </div>
        {recentAlerts.length === 0 ? (
          <EmptyState title="No new alerts" body="High-risk consumers will appear here as soon as they're detected." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Consumer</th>
                  <th>Severity</th>
                  <th>Message</th>
                  <th>Detected</th>
                </tr>
              </thead>
              <tbody>
                {recentAlerts.map((a) => (
                  <tr key={a.id}>
                    <td className="cons-id">{a.cons_no}</td>
                    <td>
                      <RiskBadge category={a.severity} />
                    </td>
                    <td className="text-mid">{a.message}</td>
                    <td className="text-sm text-dim mono">{formatDateTime(a.created_at)}</td>
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

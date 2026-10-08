import { useEffect, useState } from "react";
import { useDatasets } from "../context/DatasetContext";
import { api } from "../api/client";
import { RiskBadge, StatCard, EmptyState, GridPulse, Banner } from "../components/Common";
import FeederTrendChart from "../components/FeederTrendChart";

export default function FeedersPage() {
  const { activeDataset, activeDatasetId } = useDatasets();
  const [summary, setSummary] = useState(null);
  const [feeders, setFeeders] = useState([]);
  const [riskFilter, setRiskFilter] = useState("");
  const [selectedFeeder, setSelectedFeeder] = useState(null);
  const [trend, setTrend] = useState(null);
  const [loading, setLoading] = useState(false);
  const [trendLoading, setTrendLoading] = useState(false);
  const [error, setError] = useState("");
  const [noFeederData, setNoFeederData] = useState(false);

  useEffect(() => {
    if (!activeDatasetId || activeDataset?.status !== "completed") {
      setSummary(null);
      setFeeders([]);
      return;
    }
    setLoading(true);
    setError("");
    setNoFeederData(false);
    setSelectedFeeder(null);
    setTrend(null);

    Promise.all([
      api.getFeederSummary(activeDatasetId).catch((e) => {
        if (e.status === 404) {
          setNoFeederData(true);
          return null;
        }
        throw e;
      }),
      api.listFeeders(activeDatasetId, riskFilter ? { risk_category: riskFilter } : undefined),
    ])
      .then(([s, list]) => {
        setSummary(s);
        setFeeders(list);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [activeDatasetId, activeDataset?.status, riskFilter]);

  const openFeeder = (feeder) => {
    setSelectedFeeder(feeder);
    setTrendLoading(true);
    api
      .getFeederTrend(activeDatasetId, feeder.id)
      .then(setTrend)
      .catch((e) => setError(e.message))
      .finally(() => setTrendLoading(false));
  };

  if (!activeDataset) {
    return <EmptyState title="No dataset selected" body="Upload and select a dataset to see feeder-level loss data." />;
  }

  if (activeDataset.status !== "completed") {
    return <EmptyState title="Dataset still processing" body="Feeder loss data will appear once processing finishes." />;
  }

  return (
    <div className="flex-col gap-5">
      <div>
        <h2>Network Loss (Feeders)</h2>
        <p className="mt-2">
          Aggregate consumption per feeder vs. its own recent baseline &mdash; a network-level view that individual
          consumer anomalies alone can miss.
        </p>
      </div>

      {error && <Banner type="error">{error}</Banner>}

      {noFeederData && (
        <Banner type="info">
          No feeder data for this dataset yet &mdash; it was likely processed before this feature was added. Run{" "}
          <code className="mono">scripts/backfill_feeder_loss.py</code> on the backend, or re-upload the dataset.
        </Banner>
      )}

      {summary && (
        <>
          {summary.is_synthetic && (
            <Banner type="info">
              This source file has no feeder/area/transformer column, so consumers were auto-grouped into{" "}
              {summary.feeder_count} synthetic feeders of ~250 for demonstration. Upload a file with a{" "}
              <code className="mono">FEEDER</code> or <code className="mono">AREA</code> column to use real grid
              topology instead.
            </Banner>
          )}

          <div className="stat-grid">
            <StatCard label="Estimated network-wide loss" value={`${summary.overall_loss_pct.toFixed(1)}%`} accent="high" />
            <StatCard label="Total billed" value={`${summary.total_billed_kwh.toLocaleString()} kWh`} />
            <StatCard label="Total expected" value={`${summary.total_expected_kwh.toLocaleString()} kWh`} />
            <StatCard label="High-risk feeders" value={summary.high_risk_feeders} accent="high" />
          </div>
        </>
      )}

      {summary && (
        <div className="panel">
          <div className="panel-header">
            <h3>Feeders</h3>
            <select className="select" value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)}>
              <option value="">All risk levels</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </div>

          {loading ? (
            <div className="panel-pad">
              <GridPulse />
            </div>
          ) : feeders.length === 0 ? (
            <EmptyState title="No feeders match this filter" body="Try a different risk level." />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Feeder</th>
                    <th>Consumers</th>
                    <th>Avg loss</th>
                    <th>Peak loss</th>
                    <th>Loss-event days</th>
                    <th>Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {feeders.map((f) => (
                    <tr
                      key={f.id}
                      onClick={() => openFeeder(f)}
                      className={selectedFeeder?.id === f.id ? "row-selected" : ""}
                      style={{ cursor: "pointer" }}
                    >
                      <td className="mono">{f.feeder_code}</td>
                      <td>{f.consumer_count.toLocaleString()}</td>
                      <td className="mono">{f.avg_loss_pct.toFixed(1)}%</td>
                      <td className="mono">{f.peak_loss_pct.toFixed(1)}%</td>
                      <td>{f.loss_event_days}</td>
                      <td>
                        <RiskBadge category={f.risk_category} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {selectedFeeder && (
        <div className="panel">
          <div className="panel-header">
            <h3>{selectedFeeder.feeder_code} &mdash; billed vs. expected</h3>
          </div>
          <div className="panel-pad" style={{ height: 300 }}>
            {trendLoading ? <GridPulse /> : trend ? (
              <FeederTrendChart dates={trend.dates} billedKwh={trend.billed_kwh} expectedKwh={trend.expected_kwh} />
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

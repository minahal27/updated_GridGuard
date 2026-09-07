import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot } from "recharts";
import { api } from "../api/client";
import RiskGauge from "../components/RiskGauge";
import { GridPulse, Banner, RiskBadge } from "../components/Common";
import { formatDateTime } from "../utils/datetime";

export default function ConsumerDetailPage() {
  const { datasetId, consumerId } = useParams();
  const [series, setSeries] = useState(null);
  const [result, setResult] = useState(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    Promise.all([
      api.getTimeseries(datasetId, consumerId, { start_date: dateFrom || undefined, end_date: dateTo || undefined }),
      api.getConsumerResult(datasetId, consumerId),
    ])
      .then(([ts, res]) => {
        setSeries(ts);
        setResult(res);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId, consumerId]);

  if (loading) return <GridPulse label="Loading consumption history" />;
  if (error) return <Banner type="error">{error}</Banner>;
  if (!series || !result) return null;

  const chartData = series.points.map((p) => ({
    date: p.date,
    value: p.value,
    isAnomaly: series.anomaly_dates.includes(p.date),
  }));
  const anomalyPoints = chartData.filter((d) => d.isAnomaly && d.value !== null);

  return (
    <div className="flex-col gap-5">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/anomalies" className="text-sm">
            &larr; Back to results
          </Link>
          <h2 className="mt-2">
            Consumer <span className="mono">{series.cons_no}</span>
          </h2>
        </div>
        <RiskBadge category={result.risk_category} />
      </div>

      <div className="flex gap-5" style={{ flexWrap: "wrap" }}>
        <div className="panel panel-pad flex-col items-center" style={{ minWidth: 180 }}>
          <RiskGauge score={result.risk_score} category={result.risk_category} size={140} label="Risk score" />
        </div>

        <div className="panel panel-pad" style={{ flex: 1, minWidth: 280 }}>
          <div className="flex-col gap-3">
            <StatRow label="Isolation Forest" value={result.isoforest_anomaly ? "Flagged anomalous" : "Normal"} />
            <StatRow label="Isolation Forest score" value={(result.isoforest_score * 100).toFixed(1)} />
            <StatRow label="Risk source" value={result.risk_source} />
            <StatRow
              label="Actual label"
              value={result.actual_flag === null || result.actual_flag === undefined ? "Unlabeled" : result.actual_flag === 1 ? "Confirmed theft" : "Normal"}
            />
            <StatRow label="Detected" value={formatDateTime(result.detected_at)} />
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h3>Consumption trend</h3>
          <div className="flex gap-2 items-center">
            <input className="input" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            <span className="text-dim text-sm">to</span>
            <input className="input" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            <button className="btn btn-ghost btn-sm" onClick={load}>
              Apply
            </button>
          </div>
        </div>
        <div className="panel-pad" style={{ height: 360 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
              <CartesianGrid stroke="var(--hairline)" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fill: "var(--text-dim)", fontSize: 11 }}
                minTickGap={40}
                stroke="var(--hairline-strong)"
              />
              <YAxis tick={{ fill: "var(--text-dim)", fontSize: 11 }} stroke="var(--hairline-strong)" width={48} />
              <Tooltip
                contentStyle={{ background: "var(--bg-panel-raised)", border: "1px solid var(--hairline-strong)", borderRadius: 8 }}
                labelStyle={{ color: "var(--text-hi)" }}
              />
              <Line type="monotone" dataKey="value" stroke="var(--cyan)" strokeWidth={1.75} dot={false} connectNulls />
              {anomalyPoints.map((p) => (
                <ReferenceDot key={p.date} x={p.date} y={p.value} r={4} fill="var(--risk-high)" stroke="none" />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="panel-pad" style={{ paddingTop: 0 }}>
          <span className="text-sm text-dim">
            <span style={{ color: "var(--risk-high)" }}>&#9679;</span> marks days flagged as sudden drops/spikes relative to this consumer's own average.
          </span>
        </div>
      </div>
    </div>
  );
}

function StatRow({ label, value }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-dim">{label}</span>
      <span className="mono text-sm" style={{ color: "var(--text-hi)" }}>
        {value}
      </span>
    </div>
  );
}

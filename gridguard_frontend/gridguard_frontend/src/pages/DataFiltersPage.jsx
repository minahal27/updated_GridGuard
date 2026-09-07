import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot } from "recharts";
import { useDatasets } from "../context/DatasetContext";
import { api } from "../api/client";
import { Banner, GridPulse, RiskBadge, EmptyState } from "../components/Common";
import { formatDateTime } from "../utils/datetime";

export default function DataFiltersPage() {
  const { activeDatasetId, activeDataset } = useDatasets();
  
  const [consumerId, setConsumerId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  
  const [series, setSeries] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleApplyFilter = async () => {
    if (!activeDatasetId) {
      setError("Please select a dataset first.");
      return;
    }
    if (!consumerId) {
      setError("Please enter a Consumer ID.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      // Resolve string cons_no to numeric consumer_id if necessary
      let numericId = parseInt(consumerId, 10);
      if (isNaN(numericId) || String(numericId) !== consumerId) {
        const searchResults = await api.searchConsumers(activeDatasetId, consumerId);
        const match = searchResults.find(r => r.cons_no === consumerId);
        if (!match) {
          throw new Error("Consumer not found in this dataset.");
        }
        numericId = match.consumer_id;
      }

      const ts = await api.getTimeseries(activeDatasetId, numericId, { start_date: dateFrom || undefined, end_date: dateTo || undefined });
      setSeries(ts);
        
      // Mocking the table data based on the anomaly dates in the timeseries
      if (ts && ts.anomaly_dates) {
        const anomalyEvents = ts.anomaly_dates.map((date, index) => ({
          id: `${ts.cons_no}-${date}-${index}`,
          time: date,
          consumerId: numericId, // Use numeric ID for the review link
          consNo: ts.cons_no, // Keep string ID for display
          severity: "High", 
          status: index % 2 === 0 ? "Reviewed" : "Unresolved"
        }));
        setAnomalies(anomalyEvents);
      } else {
        setAnomalies([]);
      }
    } catch (e) {
      setError(e.message || "Failed to fetch data.");
      setSeries(null);
      setAnomalies([]);
    } finally {
      setLoading(false);
    }
  };

  const chartData = series?.points?.map((p) => ({
    date: p.date,
    value: p.value,
    isAnomaly: series.anomaly_dates.includes(p.date),
  })) || [];

  return (
    <div className="flex-col gap-5">
      <div>
        <h2>Data Filters</h2>
      </div>

      <div className="panel panel-pad">
        <h3 className="mb-4">Filter</h3>
        <div className="flex items-end gap-4" style={{ flexWrap: "wrap" }}>
          <div className="field" style={{ minWidth: 200, flex: 1 }}>
            <label>Consumer ID</label>
            <input 
              className="input" 
              type="text" 
              placeholder="e.g. 100345" 
              value={consumerId}
              onChange={(e) => setConsumerId(e.target.value)}
            />
          </div>
          
          <div className="field" style={{ minWidth: 150 }}>
            <label>Start Date</label>
            <input 
              className="input" 
              type="date" 
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </div>
          
          <div className="field" style={{ minWidth: 150 }}>
            <label>End Date</label>
            <input 
              className="input" 
              type="date" 
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>

          <button className="btn btn-primary" onClick={handleApplyFilter} disabled={loading}>
            {loading ? "Applying..." : "Apply Filter"}
          </button>
        </div>
      </div>

      {error && <Banner type="error">{error}</Banner>}

      <div className="panel">
        <div className="panel-header">
          <h3>Electricity Consumption</h3>
        </div>
        <div className="panel-pad" style={{ height: 300 }}>
          {loading ? (
            <GridPulse label="Loading chart data..." />
          ) : !series ? (
            <EmptyState title="No data" body="Enter a consumer ID and apply filters to view consumption." />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                <CartesianGrid stroke="var(--hairline)" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "var(--text-dim)", fontSize: 11 }} tickMargin={12} minTickGap={30} />
                <YAxis tick={{ fill: "var(--text-dim)", fontSize: 11 }} tickMargin={8} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: "var(--bg-panel-raised)", borderColor: "var(--hairline)" }}
                  itemStyle={{ color: "var(--text-hi)" }}
                  labelStyle={{ color: "var(--text-dim)", marginBottom: "4px" }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="var(--text-mid)"
                  strokeWidth={2}
                  dot={{ r: 4, fill: "var(--bg-panel)", strokeWidth: 2 }}
                  activeDot={{ r: 6, fill: "var(--cyan)", strokeWidth: 0 }}
                />
                {chartData.map((d, i) =>
                  d.isAnomaly && d.value !== null ? (
                    <ReferenceDot
                      key={`anomaly-${i}`}
                      x={d.date}
                      y={d.value}
                      r={5}
                      fill="var(--risk-high)"
                      stroke="var(--bg-panel)"
                      strokeWidth={2}
                    />
                  ) : null
                )}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h3>Anomalies</h3>
        </div>
        
        {series && (
          <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--hairline)', backgroundColor: 'var(--bg-panel-raised)', fontSize: '13px', color: 'var(--text-mid)' }}>
            Showing anomalies {dateFrom ? `from ${dateFrom}` : ""} {dateTo ? `to ${dateTo}` : ""} for Consumer ID: {consumerId}
          </div>
        )}

        {loading ? (
          <div className="panel-pad"><GridPulse label="Loading anomalies..." /></div>
        ) : !series ? (
          <div className="panel-pad"><EmptyState title="No anomalies" body="Apply filters to view anomalies for a specific consumer." /></div>
        ) : anomalies.length === 0 ? (
          <div className="panel-pad"><EmptyState title="No anomalies found" body="No anomalous behavior detected for this period." /></div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Consumer ID</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th style={{ width: 100 }}></th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((anomaly) => (
                  <tr key={anomaly.id}>
                    <td>{anomaly.time}</td>
                    <td className="mono">{anomaly.consNo}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: 'var(--risk-high)' }}></div>
                        {anomaly.severity}
                      </div>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: anomaly.status === 'Reviewed' ? 'var(--text-dim)' : 'var(--risk-high)' }}></div>
                        <span style={{ color: anomaly.status === 'Reviewed' ? 'var(--text-dim)' : 'inherit' }}>{anomaly.status}</span>
                      </div>
                    </td>
                    <td>
                      <Link to={`/consumers/${activeDatasetId}/${anomaly.consumerId}`} className="btn btn-ghost btn-sm" style={{ border: '1px solid var(--hairline)' }}>
                        Review
                      </Link>
                    </td>
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

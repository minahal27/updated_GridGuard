import { useEffect, useState } from "react";
import { useDatasets } from "../context/DatasetContext";
import { api } from "../api/client";
import { EmptyState, GridPulse, Banner } from "../components/Common";
import { formatDateTime } from "../utils/datetime";

export default function ReportsPage() {
  const { activeDatasetId, activeDataset } = useDatasets();
  const [format, setFormat] = useState("csv");
  const [riskFilter, setRiskFilter] = useState("");
  const [consumerFilter, setConsumerFilter] = useState("");
  const [generating, setGenerating] = useState(false);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [downloadingId, setDownloadingId] = useState(null);

  const loadReports = () => {
    if (!activeDatasetId) return;
    setLoading(true);
    api
      .listReports(activeDatasetId)
      .then(setReports)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(loadReports, [activeDatasetId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    try {
      await api.generateReport({
        dataset_id: activeDatasetId,
        format,
        risk_filter: riskFilter || undefined,
        consumer_filter: consumerFilter || undefined,
      });
      loadReports();
    } catch (e) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (report) => {
    setDownloadingId(report.id);
    try {
      await api.downloadReport(report.id, `gridguard_report_${report.id}.${report.format}`);
    } catch (e) {
      setError(e.message);
    } finally {
      setDownloadingId(null);
    }
  };

  if (!activeDataset || activeDataset.status !== "completed") {
    return <EmptyState title="No processed dataset selected" body="Select a completed dataset to generate reports." />;
  }

  return (
    <div className="flex-col gap-5">
      <div>
        <h2>Reports</h2>
        <p className="mt-2">Export anomaly and risk findings as CSV or PDF.</p>
      </div>

      {error && <Banner type="error">{error}</Banner>}

      <div className="panel panel-pad flex items-end gap-4" style={{ flexWrap: "wrap" }}>
        <div className="field">
          <label>Format</label>
          <select className="select" value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="csv">CSV</option>
            <option value="pdf">PDF</option>
          </select>
        </div>
        <div className="field">
          <label>Risk filter</label>
          <select className="select" value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)}>
            <option value="">All</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </div>
        <div className="field" style={{ minWidth: 200 }}>
          <label>Consumer ID contains</label>
          <input className="input" value={consumerFilter} onChange={(e) => setConsumerFilter(e.target.value)} placeholder="optional" />
        </div>
        <button className="btn btn-primary" onClick={handleGenerate} disabled={generating}>
          {generating ? "Generating&hellip;" : "Generate report"}
        </button>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h3>Generated reports</h3>
        </div>
        {loading ? (
          <GridPulse label="Loading reports" />
        ) : reports.length === 0 ? (
          <EmptyState title="No reports yet" body="Reports you generate will appear here for download." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Format</th>
                  <th>Generated</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.id}>
                    <td className="mono" style={{ textTransform: "uppercase" }}>
                      {r.format}
                    </td>
                    <td className="text-sm text-dim mono">{formatDateTime(r.generated_at)}</td>
                    <td>
                      <button className="btn btn-ghost btn-sm" disabled={downloadingId === r.id} onClick={() => handleDownload(r)}>
                        {downloadingId === r.id ? "Downloading&hellip;" : "Download"}
                      </button>
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

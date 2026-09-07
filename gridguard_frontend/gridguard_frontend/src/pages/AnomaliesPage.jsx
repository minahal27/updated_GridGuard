import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useDatasets } from "../context/DatasetContext";
import { api } from "../api/client";
import { RiskBadge, EmptyState, GridPulse, Banner } from "../components/Common";

const PAGE_SIZE = 25;

export default function AnomaliesPage() {
  const { activeDatasetId, activeDataset } = useDatasets();
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [riskFilter, setRiskFilter] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setPage(1);
  }, [riskFilter, search, activeDatasetId]);

  useEffect(() => {
    if (!activeDatasetId || activeDataset?.status !== "completed") return;
    setLoading(true);
    setError("");
    api
      .listAnomalies(activeDatasetId, {
        risk_category: riskFilter || undefined,
        consumer_search: search || undefined,
        page,
        page_size: PAGE_SIZE,
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [activeDatasetId, activeDataset?.status, riskFilter, search, page]);

  if (!activeDataset || activeDataset.status !== "completed") {
    return <EmptyState title="No processed dataset selected" body="Upload and select a dataset to view anomaly results." />;
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="flex-col gap-5">
      <div>
        <h2>Anomaly results</h2>
        <p className="mt-2">Consumers ranked by risk score, from the active detection model.</p>
      </div>

      <div className="panel panel-pad flex items-center gap-4" style={{ flexWrap: "wrap" }}>
        <div className="field" style={{ minWidth: 220 }}>
          <label>Search consumer ID</label>
          <input className="input" placeholder="e.g. 1000345" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="field">
          <label>Risk category</label>
          <select className="select" value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)}>
            <option value="">All</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </div>
      </div>

      {error && <Banner type="error">{error}</Banner>}

      <div className="panel">
        {loading ? (
          <GridPulse label="Loading results" />
        ) : !data || data.items.length === 0 ? (
          <EmptyState title="No results found" body="Try a different filter or search term." />
        ) : (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Consumer</th>
                    <th>Risk score</th>
                    <th>Risk category</th>
                    <th>Isolation Forest</th>
                    <th>Actual label</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((r) => (
                    <tr key={r.id}>
                      <td className="cons-id">{r.cons_no}</td>
                      <td className="mono">{(r.risk_score * 100).toFixed(1)}</td>
                      <td>
                        <RiskBadge category={r.risk_category} />
                      </td>
                      <td className="text-sm text-mid">{r.isoforest_anomaly ? "Anomalous" : "Normal"}</td>
                      <td className="text-sm text-mid">
                        {r.actual_flag === null || r.actual_flag === undefined ? "—" : r.actual_flag === 1 ? "Theft" : "Normal"}
                      </td>
                      <td>
                        <Link className="btn btn-ghost btn-sm" to={`/consumers/${activeDatasetId}/${r.consumer_id}`}>
                          View trend
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between" style={{ padding: "var(--sp-4) var(--sp-5)" }}>
              <span className="text-sm text-dim">
                {data.total.toLocaleString()} consumers &middot; page {page} of {totalPages}
              </span>
              <div className="flex gap-2">
                <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </button>
                <button className="btn btn-ghost btn-sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

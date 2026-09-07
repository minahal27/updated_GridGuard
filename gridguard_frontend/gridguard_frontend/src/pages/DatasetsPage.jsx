import { useRef, useState, useEffect } from "react";
import { useDatasets } from "../context/DatasetContext";
import { api } from "../api/client";
import { StatusBadge, Banner, EmptyState } from "../components/Common";
import { formatDateTime } from "../utils/datetime";

export default function DatasetsPage() {
  const { datasets, refresh, setActiveDatasetId } = useDatasets();
  const fileInput = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);

  // Poll while any dataset is still processing so status badges update live.
  useEffect(() => {
    const hasPending = datasets.some((d) => d.status === "processing" || d.status === "uploaded");
    if (!hasPending) return;
    const interval = setInterval(refresh, 4000);
    return () => clearInterval(interval);
  }, [datasets, refresh]);

  const handleFile = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Only CSV files are supported.");
      return;
    }
    setError("");
    setUploading(true);
    try {
      const dataset = await api.uploadDataset(file);
      await refresh();
      setActiveDatasetId(dataset.id);
    } catch (err) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex-col gap-5">
      <div>
        <h2>Datasets</h2>
        <p className="mt-2">Upload electricity consumption data (CSV) for anomaly analysis.</p>
      </div>

      {error && <Banner type="error">{error}</Banner>}

      <div
        className="panel panel-pad"
        style={{
          borderStyle: "dashed",
          borderColor: dragOver ? "var(--cyan)" : "var(--hairline-strong)",
          textAlign: "center",
          cursor: "pointer",
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFile(e.dataTransfer.files?.[0]);
        }}
        onClick={() => fileInput.current?.click()}
      >
        <input
          ref={fileInput}
          type="file"
          accept=".csv"
          style={{ display: "none" }}
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        <p style={{ color: "var(--text-hi)", fontWeight: 600 }}>
          {uploading ? "Uploading&hellip;" : "Drop a CSV here, or click to browse"}
        </p>
        <p className="text-sm mt-2">
          Expected format: one row per consumer, columns for Consumer ID, optional theft label (FLAG),
          and one column per date.
        </p>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h3>Upload history</h3>
        </div>
        {datasets.length === 0 ? (
          <EmptyState title="No datasets uploaded yet" body="Your uploaded datasets will appear here." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>File</th>
                  <th>Status</th>
                  <th>Consumers</th>
                  <th>Uploaded</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((d) => (
                  <tr key={d.id}>
                    <td>{d.file_name}</td>
                    <td>
                      <StatusBadge status={d.status} />
                    </td>
                    <td className="mono">{d.record_count ? d.record_count.toLocaleString() : "—"}</td>
                    <td className="text-sm text-dim mono">{formatDateTime(d.uploaded_at)}</td>
                    <td>
                      {d.status === "completed" && (
                        <button className="btn btn-ghost btn-sm" onClick={() => setActiveDatasetId(d.id)}>
                          Set active
                        </button>
                      )}
                      {d.status === "failed" && (
                        <span className="text-sm" style={{ color: "var(--risk-high)" }}>
                          {d.error_message}
                        </span>
                      )}
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

import { Fragment, useEffect, useState } from "react";
import { useDatasets } from "../context/DatasetContext";
import { api } from "../api/client";
import { EmptyState, GridPulse, Banner } from "../components/Common";
import { formatDateTime } from "../utils/datetime";

export default function MLModelsPage() {
  const { activeDatasetId, activeDataset } = useDatasets();
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [retraining, setRetraining] = useState(false);
  const [expandedId, setExpandedId] = useState(null);

  const load = () => {
    setLoading(true);
    api
      .listModels()
      .then(setModels)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleActivate = async (id) => {
    setBusyId(id);
    try {
      await api.activateModel(id);
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  };

  const handleRetrain = async () => {
    if (!activeDatasetId) return;
    setRetraining(true);
    setError("");
    try {
      await api.retrainModel({ dataset_id: activeDatasetId, model_name: "GridGuard-Manual" });
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setRetraining(false);
    }
  };

  return (
    <div className="flex-col gap-5">
      <div className="flex items-center justify-between">
        <div>
          <h2>ML models</h2>
          <p className="mt-2">Manage which trained model powers anomaly detection, or retrain on the active dataset.</p>
        </div>
        <button className="btn btn-primary" onClick={handleRetrain} disabled={retraining || !activeDataset || activeDataset.status !== "completed"}>
          {retraining ? "Retraining&hellip;" : `Retrain on ${activeDataset?.file_name || "active dataset"}`}
        </button>
      </div>

      {error && <Banner type="error">{error}</Banner>}
      {retraining && (
        <div className="panel panel-pad">
          <GridPulse label="Training model - cross-validating and tuning threshold" />
        </div>
      )}

      <div className="panel">
        {loading ? (
          <GridPulse label="Loading models" />
        ) : models.length === 0 ? (
          <EmptyState title="No models trained yet" body="Models are created automatically when a dataset is processed." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Algorithm</th>
                  <th>Trained</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {models.map((m) => (
                  <Fragment key={m.id}>
                    <tr>
                      <td className="mono">
                        {m.model_name} v{m.model_version}
                      </td>
                      <td className="text-sm text-mid">{m.algorithm_type}</td>
                      <td className="text-sm text-dim mono">{formatDateTime(m.uploaded_at)}</td>
                      <td>
                        {m.is_active ? (
                          <span className="badge badge-low">Active</span>
                        ) : (
                          <span className="badge badge-neutral">Inactive</span>
                        )}
                      </td>
                      <td>
                        <div className="flex gap-2">
                          {m.metrics && (
                            <button className="btn btn-ghost btn-sm" onClick={() => setExpandedId(expandedId === m.id ? null : m.id)}>
                              {expandedId === m.id ? "Hide metrics" : "View metrics"}
                            </button>
                          )}
                          {!m.is_active && (
                            <button className="btn btn-primary btn-sm" disabled={busyId === m.id} onClick={() => handleActivate(m.id)}>
                              Activate
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                    {expandedId === m.id && m.metrics && (
                      <tr>
                        <td colSpan={5} style={{ background: "rgba(255, 255, 255, 0.03)", backdropFilter: "blur(8px)" }}>
                          <MetricsPanel metrics={m.metrics} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function MetricsPanel({ metrics }) {
  const tuned = metrics.held_out_test?.tuned_threshold;
  const cv = metrics.cross_validation_5fold;
  if (!tuned) return <pre className="mono text-sm">{JSON.stringify(metrics, null, 2)}</pre>;

  return (
    <div className="flex-col gap-3" style={{ padding: "var(--sp-4)" }}>
      <div className="flex gap-5" style={{ flexWrap: "wrap" }}>
        <Metric label="Precision" value={tuned.precision} />
        <Metric label="Recall" value={tuned.recall} />
        <Metric label="F1" value={tuned.f1_score} />
        <Metric label="ROC-AUC" value={metrics.held_out_test.roc_auc} />
        <Metric label="PR-AUC" value={metrics.held_out_test.pr_auc} />
      </div>
      {cv && (
        <p className="text-sm text-dim">
          5-fold CV F1: {cv.f1.mean} (&plusmn;{cv.f1.std}) &middot; decision threshold {metrics.decision_threshold}
        </p>
      )}
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="flex-col">
      <span className="text-sm text-dim">{label}</span>
      <span className="mono" style={{ fontSize: 18, color: "var(--cyan)" }}>
        {value}
      </span>
    </div>
  );
}

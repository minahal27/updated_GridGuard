import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Banner, GridPulse } from "../components/Common";

export default function ThresholdsPage() {
  const [medium, setMedium] = useState(0.5);
  const [high, setHigh] = useState(0.7);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api
      .getThresholds()
      .then((rows) => {
        const m = rows.find((r) => r.threshold_type === "risk_medium_cutoff");
        const h = rows.find((r) => r.threshold_type === "risk_high_cutoff");
        if (m) setMedium(m.threshold_value);
        if (h) setHigh(h.threshold_value);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setError("");
    setSaved(false);
    if (Number(medium) >= Number(high)) {
      setError("Medium-risk cutoff must be lower than the High-risk cutoff.");
      return;
    }
    setSaving(true);
    try {
      await api.updateThresholds({ risk_medium_cutoff: Number(medium), risk_high_cutoff: Number(high) });
      setSaved(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <GridPulse label="Loading thresholds" />;

  return (
    <div className="flex-col gap-5">
      <div>
        <h2>Anomaly detection thresholds</h2>
        <p className="mt-2">
          Consumers at or above the High-risk cutoff automatically generate an alert. Changes apply to
          future dataset processing and retraining runs.
        </p>
      </div>

      {error && <Banner type="error">{error}</Banner>}
      {saved && <Banner type="info">Thresholds updated successfully.</Banner>}

      <form className="panel panel-pad flex-col gap-5" onSubmit={handleSave} style={{ maxWidth: 480 }}>
        <div className="field">
          <label>Medium-risk cutoff (0-1)</label>
          <input
            className="input"
            type="number"
            min="0.01"
            max="0.99"
            step="0.01"
            value={medium}
            onChange={(e) => setMedium(e.target.value)}
          />
        </div>
        <div className="field">
          <label>High-risk cutoff (0-1)</label>
          <input
            className="input"
            type="number"
            min="0.01"
            max="0.99"
            step="0.01"
            value={high}
            onChange={(e) => setHigh(e.target.value)}
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={saving}>
          {saving ? "Saving&hellip;" : "Save thresholds"}
        </button>
      </form>
    </div>
  );
}

/*
  FeederTrendChart - one feeder's billed load vs. its own rolling-median
  expected baseline, with the shortfall (billed < expected) shaded. This
  is the drill-down chart that explains WHY a feeder got flagged: unlike
  the per-consumer chart (ConsumerDetailPage) where thresholds are fixed
  cutoffs, "expected" here is the feeder's own recent history - so a
  sustained shaded gap between the two lines IS the loss signal.

  The shading is a proper band between the two series (not just an area
  under one line): each point is split into `base` = min(billed,
  expected) and `gap` = max(0, expected - billed), stacked so the visible
  red band sits exactly between the two lines only where billed falls
  short.
*/
import { ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

function LossTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  const row = payload[0]?.payload;
  if (!row) return null;
  const lossPct = row.expected > 0 ? Math.max(0, ((row.expected - row.billed) / row.expected) * 100) : 0;

  return (
    <div
      style={{
        background: "var(--bg-panel-raised)",
        border: "1px solid var(--hairline-strong)",
        borderRadius: 8,
        padding: "8px 12px",
      }}
    >
      <div className="text-sm text-dim mono" style={{ marginBottom: 4 }}>
        {label}
      </div>
      <div className="text-sm" style={{ color: "var(--cyan)" }}>
        Billed: {row.billed.toFixed(1)} kWh
      </div>
      <div className="text-sm" style={{ color: "var(--text-dim)" }}>
        Expected: {row.expected.toFixed(1)} kWh
      </div>
      {lossPct > 0.5 && (
        <div className="text-sm" style={{ color: "var(--risk-high)" }}>
          Shortfall: {lossPct.toFixed(1)}%
        </div>
      )}
    </div>
  );
}

export default function FeederTrendChart({ dates, billedKwh, expectedKwh }) {
  const data = dates.map((d, i) => {
    const billed = billedKwh[i];
    const expected = expectedKwh[i];
    return {
      date: d,
      billed,
      expected,
      base: Math.min(billed, expected),
      gap: Math.max(0, expected - billed),
    };
  });

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="var(--hairline)" vertical={false} />
        <XAxis dataKey="date" tick={{ fill: "var(--text-dim)", fontSize: 11 }} minTickGap={48} stroke="var(--hairline-strong)" />
        <YAxis tick={{ fill: "var(--text-dim)", fontSize: 11 }} stroke="var(--hairline-strong)" width={52} />
        <Tooltip content={<LossTooltip />} />
        <Legend formatter={(value) => <span style={{ color: "var(--text-mid)", fontSize: 12 }}>{value}</span>} />

        {/* Stacked helper areas - invisible base + shaded gap - form the
            "shortfall" band exactly between the two lines. */}
        <Area dataKey="base" stackId="loss" stroke="none" fill="transparent" legendType="none" tooltipType="none" name="" />
        <Area
          dataKey="gap"
          stackId="loss"
          stroke="none"
          fill="var(--risk-high)"
          fillOpacity={0.22}
          name="Shortfall"
          tooltipType="none"
        />

        <Line type="monotone" dataKey="expected" name="Expected (baseline)" stroke="var(--text-dim)" strokeDasharray="4 3" strokeWidth={1.4} dot={false} />
        <Line type="monotone" dataKey="billed" name="Billed (actual)" stroke="var(--cyan)" strokeWidth={1.8} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

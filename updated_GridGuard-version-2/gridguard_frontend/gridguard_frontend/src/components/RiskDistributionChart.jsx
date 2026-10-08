/*
  RiskDistributionChart - donut chart summarizing the High/Medium/Low split
  for the active dataset. Reuses the same functional risk-tier colors as
  RiskBadge/RiskGauge (cyan/amber/red) so the color language stays
  consistent everywhere risk appears in the app.
*/
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";

const COLORS = {
  High: "var(--risk-high)",
  Medium: "var(--risk-medium)",
  Low: "var(--risk-low)",
};

export default function RiskDistributionChart({ high, medium, low }) {
  const data = [
    { name: "High", value: high },
    { name: "Medium", value: medium },
    { name: "Low", value: low },
  ].filter((d) => d.value > 0);

  const total = high + medium + low;

  if (total === 0) {
    return <span className="text-sm text-dim">No consumers scored yet</span>;
  }

  return (
    <div style={{ position: "relative", height: 240 }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={62}
            outerRadius={92}
            paddingAngle={3}
            stroke="var(--bg-panel)"
            strokeWidth={2}
          >
            {data.map((d) => (
              <Cell key={d.name} fill={COLORS[d.name]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ background: "var(--bg-panel-raised)", border: "1px solid var(--hairline-strong)", borderRadius: 8 }}
            labelStyle={{ color: "var(--text-hi)" }}
            formatter={(value, name) => [`${value.toLocaleString()} (${((value / total) * 100).toFixed(1)}%)`, name]}
          />
          <Legend
            verticalAlign="bottom"
            height={28}
            formatter={(value) => <span style={{ color: "var(--text-mid)", fontSize: 12 }}>{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
      {/* Center readout - total consumers scored */}
      <div
        style={{
          position: "absolute",
          top: "42%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          textAlign: "center",
          pointerEvents: "none",
        }}
      >
        <div className="mono" style={{ fontSize: 22, fontWeight: 700, color: "var(--text-hi)" }}>
          {total.toLocaleString()}
        </div>
        <div className="text-sm text-dim">consumers</div>
      </div>
    </div>
  );
}

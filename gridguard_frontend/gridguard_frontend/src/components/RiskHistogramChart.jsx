/*
  RiskHistogramChart - full risk_score distribution (0-1, 0.1-wide bins),
  not just the 3-bucket High/Medium/Low split. Lets an analyst see whether
  the current threshold cutoffs (UC13) fall on a natural break in the
  scores or slice through a dense cluster - directly useful when deciding
  whether to retune thresholds.
*/
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

export default function RiskHistogramChart({ bins }) {
  const data = bins.map((b) => ({
    label: `${b.range_start.toFixed(1)}`,
    count: b.count,
    mid: (b.range_start + b.range_end) / 2,
  }));

  const colorFor = (mid) => {
    if (mid >= 0.7) return "var(--risk-high)";
    if (mid >= 0.5) return "var(--risk-medium)";
    return "var(--risk-low)";
  };

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="var(--hairline)" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fill: "var(--text-dim)", fontSize: 11 }}
          stroke="var(--hairline-strong)"
          label={{ value: "risk score", position: "insideBottom", offset: -4, fill: "var(--text-dim)", fontSize: 11 }}
        />
        <YAxis tick={{ fill: "var(--text-dim)", fontSize: 11 }} stroke="var(--hairline-strong)" width={40} allowDecimals={false} />
        <Tooltip
          contentStyle={{ background: "var(--bg-panel-raised)", border: "1px solid var(--hairline-strong)", borderRadius: 8 }}
          labelStyle={{ color: "var(--text-hi)" }}
          formatter={(value) => [value, "consumers"]}
          labelFormatter={(label) => `score ${label} – ${(Number(label) + 0.1).toFixed(1)}`}
        />
        <Bar dataKey="count" radius={[3, 3, 0, 0]}>
          {data.map((d) => (
            <Cell key={d.label} fill={colorFor(d.mid)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

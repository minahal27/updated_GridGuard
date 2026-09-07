/*
  TopRiskConsumersChart - horizontal bar chart of the highest risk_score
  consumers in the active dataset. Bars are clickable and route straight to
  ConsumerDetailPage (the same drill-down used from AnomaliesPage), so the
  dashboard becomes a starting point for investigation, not just a summary.
*/
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { useNavigate } from "react-router-dom";
import { useDatasets } from "../context/DatasetContext";

const RISK_COLORS = {
  High: "var(--risk-high)",
  Medium: "var(--risk-medium)",
  Low: "var(--risk-low)",
};

export default function TopRiskConsumersChart({ data }) {
  const navigate = useNavigate();
  const { activeDatasetId } = useDatasets();

  const chartData = data
    .slice()
    .sort((a, b) => b.risk_score - a.risk_score)
    .map((d) => ({ ...d, scorePct: Math.round(d.risk_score * 100) }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 8, right: 24, left: 8, bottom: 8 }}
        barCategoryGap={10}
      >
        <CartesianGrid stroke="var(--hairline)" horizontal={false} />
        <XAxis type="number" domain={[0, 100]} tick={{ fill: "var(--text-dim)", fontSize: 11 }} stroke="var(--hairline-strong)" />
        <YAxis
          type="category"
          dataKey="cons_no"
          width={110}
          tick={{ fill: "var(--text-mid)", fontSize: 12, fontFamily: "var(--font-mono)" }}
          stroke="var(--hairline-strong)"
        />
        <Tooltip
          contentStyle={{ background: "var(--bg-panel-raised)", border: "1px solid var(--hairline-strong)", borderRadius: 8 }}
          labelStyle={{ color: "var(--text-hi)" }}
          formatter={(value, _name, props) => [`${value}% risk`, props.payload.risk_category]}
          cursor={{ fill: "var(--bg-panel-hover)" }}
        />
        <Bar
          dataKey="scorePct"
          radius={[0, 3, 3, 0]}
          cursor="pointer"
          onClick={(d) => navigate(`/consumers/${activeDatasetId}/${d.consumer_id}`)}
        >
          {chartData.map((d) => (
            <Cell key={d.consumer_id} fill={RISK_COLORS[d.risk_category] || "var(--text-dim)"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

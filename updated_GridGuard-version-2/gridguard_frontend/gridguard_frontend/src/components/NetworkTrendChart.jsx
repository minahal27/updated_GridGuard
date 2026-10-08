/*
  NetworkTrendChart - dataset-wide average daily consumption, distinct from
  the per-consumer trace on ConsumerDetailPage. Gives an analyst a sense of
  the overall load curve (seasonality, dips, network-wide events) that a
  single consumer's chart can't show.
*/
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function NetworkTrendChart({ dates, values }) {
  const data = dates.map((d, i) => ({ date: d, value: values[i] }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <defs>
          <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--cyan)" stopOpacity={0.35} />
            <stop offset="95%" stopColor="var(--cyan)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="var(--hairline)" vertical={false} />
        <XAxis dataKey="date" tick={{ fill: "var(--text-dim)", fontSize: 11 }} minTickGap={48} stroke="var(--hairline-strong)" />
        <YAxis tick={{ fill: "var(--text-dim)", fontSize: 11 }} stroke="var(--hairline-strong)" width={48} />
        <Tooltip
          contentStyle={{ background: "var(--bg-panel-raised)", border: "1px solid var(--hairline-strong)", borderRadius: 8 }}
          labelStyle={{ color: "var(--text-hi)" }}
          formatter={(value) => [value?.toFixed(2), "avg kWh"]}
        />
        <Area type="monotone" dataKey="value" stroke="var(--cyan)" strokeWidth={1.75} fill="url(#trendFill)" connectNulls />
      </AreaChart>
    </ResponsiveContainer>
  );
}

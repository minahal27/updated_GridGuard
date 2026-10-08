/*
  RiskGauge - the design's signature element. Renders a risk score (0-1) as
  an analog meter dial with a copper needle, echoing a physical utility
  meter rather than a generic progress bar - deliberate, since this is a
  tool about literal electricity meters.
*/
const RISK_COLORS = {
  Low: "var(--risk-low)",
  Medium: "var(--risk-medium)",
  High: "var(--risk-high)",
};

export default function RiskGauge({ score = 0, category = "Low", size = 120, label }) {
  const clamped = Math.max(0, Math.min(1, score));
  const startAngle = -120;
  const endAngle = 120;
  const angle = startAngle + clamped * (endAngle - startAngle);
  const color = RISK_COLORS[category] || "var(--text-mid)";

  const radius = size / 2 - 10;
  const cx = size / 2;
  const cy = size / 2;

  const polarToCartesian = (r, deg) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  };

  const arcPath = (from, to, r) => {
    const start = polarToCartesian(r, to);
    const end = polarToCartesian(r, from);
    const largeArc = to - from <= 180 ? 0 : 1;
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`;
  };

  const ticks = Array.from({ length: 9 }, (_, i) => startAngle + (i * (endAngle - startAngle)) / 8);
  const needleEnd = polarToCartesian(radius - 14, angle);

  return (
    <div className="flex-col items-center" style={{ gap: 4 }}>
      <svg width={size} height={size * 0.82} viewBox={`0 0 ${size} ${size}`}>
        {/* Track */}
        <path d={arcPath(startAngle, endAngle, radius)} stroke="var(--hairline-strong)" strokeWidth="8" fill="none" strokeLinecap="round" />
        {/* Value arc */}
        <path d={arcPath(startAngle, angle, radius)} stroke={color} strokeWidth="8" fill="none" strokeLinecap="round" />
        {/* Ticks */}
        {ticks.map((t, i) => {
          const inner = polarToCartesian(radius - 12, t);
          const outer = polarToCartesian(radius - 4, t);
          return (
            <line
              key={i}
              x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y}
              stroke="var(--text-dim)" strokeWidth="1.5"
            />
          );
        })}
        {/* Needle */}
        <line x1={cx} y1={cy} x2={needleEnd.x} y2={needleEnd.y} stroke={color} strokeWidth="2.5" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="5" fill={color} />
        {/* Reading */}
        <text x={cx} y={cy + radius * 0.55} textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize={size * 0.15} fontWeight="600" fill="var(--text-hi)">
          {(clamped * 100).toFixed(0)}
        </text>
      </svg>
      {label && <span className="text-sm text-dim">{label}</span>}
    </div>
  );
}

/*
  GridIllustration - an original SVG scene for the login page: transmission
  towers, sagging power lines with an animated "current flow" dash, and a
  small skyline of metered buildings where two rooftop nodes pulse red
  (flagged consumers) against the rest in steady cyan (normal). Built from
  scratch with the app's own design tokens rather than a stock photo, so
  it's copyright-safe and matches the rest of the UI exactly.
*/
export default function GridIllustration() {
  return (
    <svg
      className="auth-illustration-svg"
      viewBox="0 0 560 380"
      preserveAspectRatio="xMidYMax slice"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Ground line */}
      <line x1="0" y1="300" x2="560" y2="300" stroke="var(--hairline-strong)" strokeWidth="1" />

      {/* Skyline of metered buildings */}
      <g>
        {[
          { x: 30, w: 46, h: 70 },
          { x: 82, w: 34, h: 46 },
          { x: 122, w: 52, h: 92 },
          { x: 400, w: 40, h: 58 },
          { x: 446, w: 30, h: 40 },
          { x: 482, w: 48, h: 84 },
        ].map((b, i) => (
          <rect
            key={i}
            x={b.x}
            y={300 - b.h}
            width={b.w}
            height={b.h}
            fill="var(--bg-panel-raised)"
            stroke="var(--hairline-strong)"
            strokeWidth="1"
          />
        ))}
      </g>

      {/* Transmission towers */}
      {[70, 280, 500].map((cx, i) => (
        <g key={i} stroke="var(--hairline-strong)" strokeWidth="1.4" fill="none">
          <path d={`M${cx - 34} 300 L${cx} 90 L${cx + 34} 300`} />
          <path d={`M${cx - 22} 300 L${cx} 150 L${cx + 22} 300`} />
          <line x1={cx - 46} y1="120" x2={cx + 46} y2="120" />
          <line x1={cx - 30} y1="170" x2={cx + 30} y2="170" />
          <circle cx={cx} cy="90" r="3" fill="var(--copper)" stroke="none" />
        </g>
      ))}

      {/* Sagging cables between towers, with an animated current-flow dash */}
      {[
        "M104 118 Q 175 155 246 118",
        "M314 118 Q 385 155 456 118",
      ].map((d, i) => (
        <g key={i}>
          <path d={d} stroke="var(--hairline-strong)" strokeWidth="1.2" fill="none" />
          <path d={d} className="current-flow" stroke="var(--cyan)" strokeWidth="1.6" fill="none" strokeDasharray="2 10" />
        </g>
      ))}

      {/* Rooftop meter nodes - two flagged anomalous (red pulse), rest normal (cyan) */}
      {[
        { x: 53, y: 230, anomaly: false },
        { x: 99, y: 254, anomaly: false },
        { x: 148, y: 208, anomaly: true },
        { x: 420, y: 242, anomaly: false },
        { x: 461, y: 260, anomaly: true },
        { x: 506, y: 216, anomaly: false },
      ].map((n, i) => (
        <g key={i}>
          {n.anomaly && (
            <circle cx={n.x} cy={n.y} r="7" className="meter-anomaly-halo" fill="var(--risk-high)" opacity="0.35" />
          )}
          <circle
            cx={n.x}
            cy={n.y}
            r="3.2"
            fill={n.anomaly ? "var(--risk-high)" : "var(--cyan)"}
            className={n.anomaly ? "meter-anomaly-dot" : ""}
          />
        </g>
      ))}
    </svg>
  );
}

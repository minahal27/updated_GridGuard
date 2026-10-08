import React from 'react';
import '../styles/background.css';

export default function TheftDetectionBackground() {
  return (
    <div className="animated-bg-container">
      {/* High-Resolution Photorealistic Smart Grid Infrastructure Background */}
      <div className="smart-grid-photo-layer" />

      {/* Cyber Grid SVG Overlay with Clean Steady Transmission Infrastructure */}
      <svg className="electricity-grid-svg" viewBox="0 0 1000 600" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="liquid-glow-blue" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          
          <filter id="liquid-glow-red" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Matrix Grid Lines - Clean & Non-blinking */}
        <g stroke="rgba(255, 255, 255, 0.05)" strokeWidth="1">
          {Array.from({ length: 24 }).map((_, i) => (
            <React.Fragment key={i}>
              <line x1="0" y1={i * 45} x2="1000" y2={i * 45} />
              <line x1={i * 45} y1="0" x2={i * 45} y2="600" />
            </React.Fragment>
          ))}
        </g>

        {/* High-Voltage Primary Feeder Lines (Neon Blue) */}
        <g stroke="var(--blue-liquid)" strokeWidth="2" opacity="0.4" fill="none">
          <path d="M-20 300 L200 300 L250 180 L420 180 L470 380 L620 380 L670 230 L820 230 L870 340 L1040 340" />
          <path d="M-40 140 L260 140 L310 260 L460 260 L510 90 L720 90 L770 290 L920 290 L1020 220" />
          <path d="M120 480 L340 480 L390 320 L560 320 L610 520 L870 520 L1020 410" />
        </g>

        {/* Steady Electric Feeder Glow Trace */}
        <g stroke="var(--blue-liquid-bright)" strokeWidth="1.8" fill="none" opacity="0.7">
          <path d="M-20 300 L200 300 L250 180 L420 180 L470 380 L620 380 L670 230 L820 230 L870 340 L1040 340" strokeDasharray="30 60" />
          <path d="M-40 140 L260 140 L310 260 L460 260 L510 90 L720 90 L770 290 L920 290 L1020 220" strokeDasharray="30 60" />
          <path d="M120 480 L340 480 L390 320 L560 320 L610 520 L870 520 L1020 410" strokeDasharray="30 60" />
        </g>

        {/* Stable Substations / Meters (Steady Non-blinking Blue Nodes) */}
        {[
          {x: 200, y: 300}, {x: 250, y: 180}, {x: 420, y: 180}, {x: 670, y: 230}, {x: 820, y: 230},
          {x: 260, y: 140}, {x: 310, y: 260}, {x: 510, y: 90}, {x: 720, y: 90}, {x: 920, y: 290},
          {x: 120, y: 480}, {x: 340, y: 480}, {x: 560, y: 320}, {x: 610, y: 520}
        ].map((node, i) => (
          <g key={`normal-${i}`}>
            <circle cx={node.x} cy={node.y} r="6" fill="var(--bg-panel-deep)" stroke="var(--blue-liquid)" strokeWidth="2" filter="url(#liquid-glow-blue)" />
            <circle cx={node.x} cy={node.y} r="3" fill="var(--blue-liquid-bright)" />
          </g>
        ))}

        {/* Flagged High-Risk Anomaly Nodes (Steady Red Glow & Clear HUD Badges) */}
        {[
          {x: 470, y: 380, label: "FEEDER_LOSS_38%"}, 
          {x: 870, y: 340, label: "BYPASS_SUSPECTED"}, 
          {x: 460, y: 260, label: "METER_TAMPERED"}, 
          {x: 770, y: 290, label: "UNBILLED_DRAW"}, 
          {x: 390, y: 320, label: "ZERO_LOAD_SPIKE"}
        ].map((node, i) => (
          <g key={`anomaly-${i}`}>
            {/* Steady Outer Anomaly Aura */}
            <circle cx={node.x} cy={node.y} r="16" fill="none" stroke="var(--red-liquid)" strokeWidth="1.5" opacity="0.4" />
            
            {/* Core Red Anomaly Node */}
            <circle cx={node.x} cy={node.y} r="8" fill="var(--bg-panel-deep)" stroke="var(--red-liquid)" strokeWidth="2" filter="url(#liquid-glow-red)" />
            <circle cx={node.x} cy={node.y} r="4" fill="var(--red-liquid-bright)" />
            
            {/* Clean Stable HUD Alert Flag (Zero Blinking) */}
            <g>
              <rect x={node.x + 14} y={node.y - 22} width="115" height="18" rx="4" fill="rgba(8, 14, 30, 0.85)" stroke="var(--red-liquid)" strokeWidth="1" />
              <text x={node.x + 20} y={node.y - 10} fill="var(--red-liquid-bright)" fontSize="9" fontWeight="700" fontFamily="var(--font-mono)">
                {node.label}
              </text>
              <polyline points={`${node.x + 6},${node.y - 6} ${node.x + 14},${node.y - 13}`} fill="none" stroke="var(--red-liquid)" strokeWidth="1.2" />
            </g>
          </g>
        ))}
      </svg>
    </div>
  );
}

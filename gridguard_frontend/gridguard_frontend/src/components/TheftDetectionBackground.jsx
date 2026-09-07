import React from 'react';
import '../styles/background.css';

export default function TheftDetectionBackground() {
  return (
    <div className="animated-bg-container">
      <div className="radar-sweep"></div>
      
      <svg className="electricity-grid-svg" viewBox="0 0 1000 600" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="glow-cyan" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          
          <filter id="glow-red" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="8" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Base Grid Lines (Subtle) */}
        <g stroke="rgba(255, 255, 255, 0.03)" strokeWidth="1">
          {Array.from({ length: 20 }).map((_, i) => (
            <React.Fragment key={i}>
              <line x1="0" y1={i * 50} x2="1000" y2={i * 50} />
              <line x1={i * 50} y1="0" x2={i * 50} y2="600" />
            </React.Fragment>
          ))}
        </g>

        {/* Transmission Lines / Data Paths */}
        <g stroke="var(--cyan)" strokeWidth="1.5" opacity="0.3" fill="none">
          <path d="M50 300 L200 300 L250 200 L400 200 L450 400 L600 400 L650 250 L800 250 L850 350 L1050 350" />
          <path d="M-50 150 L250 150 L300 250 L450 250 L500 100 L700 100 L750 300 L900 300" />
          <path d="M150 450 L350 450 L400 300 L550 300 L600 500 L850 500 L1000 400" />
        </g>

        {/* Animated Current Flow (Dashed Lines) */}
        <g stroke="var(--cyan)" strokeWidth="2" fill="none" className="animated-flow">
          <path d="M50 300 L200 300 L250 200 L400 200 L450 400 L600 400 L650 250 L800 250 L850 350 L1050 350" strokeDasharray="15 30" />
          <path d="M-50 150 L250 150 L300 250 L450 250 L500 100 L700 100 L750 300 L900 300" strokeDasharray="15 30" />
          <path d="M150 450 L350 450 L400 300 L550 300 L600 500 L850 500 L1000 400" strokeDasharray="15 30" />
        </g>

        {/* Normal Meters (Cyan) */}
        {[
          {x: 200, y: 300}, {x: 250, y: 200}, {x: 400, y: 200}, {x: 650, y: 250}, {x: 800, y: 250},
          {x: 250, y: 150}, {x: 300, y: 250}, {x: 500, y: 100}, {x: 700, y: 100}, {x: 900, y: 300},
          {x: 150, y: 450}, {x: 350, y: 450}, {x: 550, y: 300}, {x: 600, y: 500}
        ].map((node, i) => (
          <g key={`normal-${i}`}>
            <circle cx={node.x} cy={node.y} r="6" fill="var(--bg-panel)" stroke="var(--cyan)" strokeWidth="1.5" filter="url(#glow-cyan)" />
            <circle cx={node.x} cy={node.y} r="3" fill="var(--cyan)" />
          </g>
        ))}

        {/* Anomalous Meters (Theft Detected - Red Pulses) */}
        {[
          {x: 450, y: 400}, {x: 850, y: 350}, {x: 450, y: 250}, {x: 750, y: 300}, {x: 400, y: 300}, {x: 850, y: 500}
        ].map((node, i) => (
          <g key={`anomaly-${i}`}>
            {/* Pulsing Ripple Effect */}
            <circle cx={node.x} cy={node.y} r="15" fill="none" stroke="var(--risk-high)" strokeWidth="2" className="anomaly-ripple" />
            <circle cx={node.x} cy={node.y} r="25" fill="none" stroke="var(--risk-high)" strokeWidth="1" className="anomaly-ripple-delay" />
            
            {/* Core Red Node */}
            <circle cx={node.x} cy={node.y} r="8" fill="var(--bg-panel)" stroke="var(--risk-high)" strokeWidth="2" filter="url(#glow-red)" />
            <circle cx={node.x} cy={node.y} r="4" fill="var(--risk-high)" className="anomaly-pulse-core" />
            
            {/* Alert Text Next to Node */}
            <text x={node.x + 15} y={node.y - 15} fill="var(--risk-high)" fontSize="11" fontFamily="monospace" className="alert-text-flicker">
              [THEFT_DETECTED]
            </text>
            <path d={`M${node.x + 10} ${node.y - 10} L${node.x + 40} ${node.y - 40} L${node.x + 100} ${node.y - 40}`} fill="none" stroke="var(--risk-high)" strokeWidth="1" opacity="0.6" className="alert-text-flicker" />
          </g>
        ))}
      </svg>
    </div>
  );
}

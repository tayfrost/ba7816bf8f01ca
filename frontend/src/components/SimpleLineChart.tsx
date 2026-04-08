import { useMemo } from "react";

type Point = { date: string; value: number };

type Props = {
  points: Point[];
  width?: number;
  height?: number;
};
export default function SimpleLineChart({ points, width = 520, height = 150 }: Props) {

  const { polyline, fillPath, min, max, latest, mid, padValue } = useMemo(() => {
    if (!points || points.length === 0) {
      return { polyline: "", fillPath: "", min: 0, max: 0, latest: 0, mid: 0, padValue: 15 };
    }

    const values = points.map((p) => p.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const latest = values[values.length - 1];
    const mid = (max + min) / 2;

    const axisPad = 40; 
    const innerPad = 15;
    const w = Math.max(1, width - innerPad - axisPad);
    const h = Math.max(1, height - innerPad * 2);

    const denom = max - min === 0 ? 1 : max - min;

    const coords = points.map((p, i) => {
      const x = axisPad + (i / Math.max(1, points.length - 1)) * w;
      const norm = (p.value - min) / denom;
      const y = innerPad + (1 - norm) * h;
      return { x, y };
    });

    const linePoints = coords.map(c => `${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
    const fillPath = `${linePoints} ${coords[coords.length - 1].x},${height} ${coords[0].x},${height} Z`;

    return { polyline: linePoints, fillPath, min, max, latest, mid, padValue: innerPad };
  }, [points, width, height]);

  if (!points || points.length === 0) return null;

  return (
    <div style={{
      width: "100%",
      background: "#2e1a41af",
      padding: "20px",
      borderRadius: "16px",
      border: "1px solid rgba(255, 255, 255, 0.1)",
      backdropFilter: "blur(8px)",
      boxSizing: "border-box",
    }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        style={{ display: "block", overflow: "visible" }}
      >
        <defs>
          <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="100%">
            <stop offset="0%" stopColor="#ef6330" stopOpacity="0.7" />
            <stop offset="30%" stopColor="#ffb347" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#ffb347" stopOpacity="0" />
          </linearGradient>

          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        <g stroke="rgba(255,255,255,0.05)" strokeWidth="1">
          <line x1="40" y1={padValue} x2={width} y2={padValue} />
          <line x1="40" y1={height / 2} x2={width} y2={height / 2} />
          <line x1="40" y1={height - padValue} x2={width} y2={height - padValue} />
        </g>

        <g fill="rgba(255,255,255,0.4)" fontSize="10" textAnchor="end">
          <text x="32" y={padValue + 4}>{max < 1 ? max.toFixed(2) : Math.round(max)}</text>
          <text x="32" y={height / 2 + 4}>{mid < 1 ? mid.toFixed(2) : Math.round(mid)}</text>
          <text x="32" y={height - padValue + 4}>{min < 1 ? min.toFixed(2) : Math.round(min)}</text>
        </g>

        <polyline points={fillPath} fill="url(#areaGradient)" stroke="none" />

        <polyline
          points={polyline}
          fill="none"
          stroke="url(#areaGradient)"
          strokeWidth={3}
          strokeLinecap="round"
          filter="url(#glow)"
        />
      </svg>

      <div style={{ 
        display: "flex", 
        justifyContent: "space-between", 
        fontSize: 12, 
        marginTop: 16,
        fontFamily: "sans-serif",
        borderTop: "1px solid rgba(255,255,255,0.1)",
        paddingTop: "12px"
      }}>
        <div style={{ color: "white" }}>MIN: <span style={{ color: "#ffb347", fontWeight: "bold" }}>{min < 1 ? min.toFixed(3) : Math.round(min)}</span></div>
        <div style={{ color: "white" }}>LATEST: <span style={{ color: "#ffb347", fontWeight: "bold" }}>{latest < 1 ? latest.toFixed(3) : Math.round(latest)}</span></div>
        <div style={{ color: "white" }}>MAX: <span style={{ color: "#ef6330", fontWeight: "bold" }}>{max < 1 ? max.toFixed(3) : Math.round(max)}</span></div>
      </div>
    </div>
  );
}
import { useMemo } from "react";

type Point = { date: string; value: number };

type Props = {
  points: Point[];
  width?: number;
  height?: number;
  /** Fixed axis maximum. Default 10 for score charts; pass 100 for the trend graph. */
  maxValue?: number;
};
export default function SimpleLineChart({ points, width = 520, height = 150, maxValue = 10 }: Props) {

  const workingPoints = useMemo(() => {
    if (!points || points.length === 0) {
      // No data at all — flat zero line for today's window (polling fills in real data)
      const today = new Date();
      return Array.from({ length: 7 }, (_, i) => {
        const d = new Date(today);
        d.setDate(today.getDate() - (6 - i));
        return { date: d.toISOString().slice(0, 10), value: 0 };
      });
    }
    if (points.length === 1) {
      // Single point — prepend a zero the day before so a line can be drawn
      const firstDate = new Date(`${points[0].date}T00:00:00`);
      firstDate.setDate(firstDate.getDate() - 1);
      return [{ date: firstDate.toISOString().slice(0, 10), value: 0 }, ...points];
    }
    return points;
  }, [points]);

  const { polyline, fillPath, min, max, latest, mid, padValue } = useMemo(() => {
    const pts = workingPoints;

    const rawValues = pts.map((p) => p.value);
    const allZero = rawValues.every((v) => v === 0);

    // Clamp every value to [0, maxValue] (guard against out-of-range scores)
    const values = allZero
      ? rawValues
      : rawValues.map((v) => Math.min(maxValue, Math.max(0, v)));

    // Axis bounds: all-zero keeps flat-line behaviour; non-zero fixes to [0, maxValue]
    const axisMax = allZero ? 0 : maxValue;
    const denom   = allZero ? 1 : maxValue;  // allZero: denom=1 triggers flat-line path below

    const latest = values[values.length - 1];
    const min = 0;
    const max = allZero ? 0 : axisMax;
    const mid = allZero ? 0 : maxValue / 2;

    const axisPad = 40;
    const innerPad = 15;
    const w = Math.max(1, width - innerPad - axisPad);
    const h = Math.max(1, height - innerPad * 2);

    const coords = pts.map((p, i) => {
      const v = allZero ? p.value : Math.min(maxValue, Math.max(0, p.value));
      const x = axisPad + (i / Math.max(1, pts.length - 1)) * w;
      // All-zero: render flat line at vertical midpoint (same as before)
      const y = allZero ? height / 2 : innerPad + (1 - v / denom) * h;
      return { x, y };
    });

    const linePoints = coords.map(c => `${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
    const fillPath = `${linePoints} ${coords[coords.length - 1].x},${height} ${coords[0].x},${height} Z`;

    return { polyline: linePoints, fillPath, min, max, latest, mid, padValue: innerPad };
  }, [workingPoints, width, height]);

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
          <text x="32" y={padValue + 4}>{max}</text>
          <text x="32" y={height / 2 + 4}>{mid}</text>
          <text x="32" y={height - padValue + 4}>{min}</text>
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
        <div style={{ color: "white" }}>MIN: <span style={{ color: "#ffb347", fontWeight: "bold" }}>{min}</span></div>
        <div style={{ color: "white" }}>LATEST: <span style={{ color: "#ffb347", fontWeight: "bold" }}>{latest}</span></div>
        <div style={{ color: "white" }}>MAX: <span style={{ color: "#ef6330", fontWeight: "bold" }}>{max}</span></div>
      </div>
    </div>
  );
}
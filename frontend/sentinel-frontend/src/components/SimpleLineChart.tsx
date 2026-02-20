import { useMemo } from "react";

type Point = { date: string; value: number };

type Props = {
  points: Point[];
  width?: number;
  height?: number;
};

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

export default function SimpleLineChart({ points, width = 520, height = 120 }: Props) {
  const { polyline, min, max, latest } = useMemo(() => {
    if (!points || points.length === 0) {
      return { polyline: "", min: 0, max: 0, latest: 0 };
    }

    const values = points.map((p) => p.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const latest = values[values.length - 1];

    const innerPad = 8;
    const w = Math.max(1, width - innerPad * 2);
    const h = Math.max(1, height - innerPad * 2);

    const denom = max - min === 0 ? 1 : max - min;

    const coords = points.map((p, i) => {
      const x = innerPad + (i / Math.max(1, points.length - 1)) * w;
      const norm = (p.value - min) / denom; // 0..1
      const y = innerPad + (1 - norm) * h;  // invert so higher is up
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });

    return { polyline: coords.join(" "), min, max, latest };
  }, [points, width, height]);

  if (!points || points.length === 0) {
    return (
      <div style={{ opacity: 0.7, fontSize: 12 }}>
        No data available.
      </div>
    );
  }

  return (
    <div>
      <svg width={width} height={height} style={{ display: "block" }}>
        {/* frame */}
        <rect
          x={0}
          y={0}
          width={width}
          height={height}
          rx={10}
          ry={10}
          fill="transparent"
          stroke="rgba(255,255,255,0.12)"
        />
        {/* line */}
        <polyline
          points={polyline}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
        />
      </svg>

      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, opacity: 0.8, marginTop: 6 }}>
        <span>min: {min}</span>
        <span>latest: {latest}</span>
        <span>max: {max}</span>
      </div>
    </div>
  );
}
import { getRiskLevel } from "../../types/employees";

type Props = {
  score: number;
};

const COLORS = {
  low: "#2ecc71",
  medium: "#f1c40f",
  high: "#ff7a18",
  critical: "#ff3b30",
};

export default function RiskBadge({ score }: Props) {
  const level = getRiskLevel(score);
  const color = COLORS[level];

  return (
    <div
      style={{
        padding: "6px 12px",
        borderRadius: "20px",
        fontSize: "11px",
        fontWeight: 900,
        letterSpacing: "1px",
        background: `${color}22`,
        border: `1px solid ${color}`,
        color,
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
      }}
    >
      {level.toUpperCase()}
      <span style={{ opacity: 0.7 }}>({score})</span>
    </div>
  );
}
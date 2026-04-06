type Props = {
  value: number;
};

function getColor(value: number) {
  if (value >= 85) return "#ff3b30";
  if (value >= 65) return "#ff7a18";
  if (value >= 35) return "#f1c40f";
  return "#2ecc71";
}

export default function RiskProgressBar({ value }: Props) {
  const color = getColor(value);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: "160px" }}>
      <div
        style={{
          flex: 1,
          height: "8px",
          borderRadius: "999px",
          background: "rgba(255,255,255,0.08)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${Math.max(0, Math.min(100, value))}%`,
            height: "100%",
            background: color,
            borderRadius: "999px",
          }}
        />
      </div>

      <span style={{ fontSize: "12px", fontWeight: 800, color: "#fff", minWidth: "38px" }}>
        {value}%
      </span>
    </div>
  );
}
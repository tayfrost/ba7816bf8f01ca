import type { IncidentStats } from "../../api";

type Props = {
  stats: IncidentStats | null;
};

export default function IncidentStatsPanel({ stats }: Props) {
  if (!stats) return null;

  const sortedReasons = Object.entries(stats.by_reason).sort((a, b) => b[1] - a[1]);

  return (
    <div
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "30px",
        padding: "28px",
      }}
    >
      <h3 style={{ margin: "0 0 18px 0", fontWeight: 900, color: "#fff" }}>
        Incident Overview
      </h3>

      <div
        style={{
          padding: "16px",
          borderRadius: "18px",
          background: "rgba(255,255,255,0.04)",
          marginBottom: "18px",
        }}
      >
        <div style={{ fontSize: "11px", opacity: 0.5, textTransform: "uppercase", fontWeight: 900 }}>
          Total incidents
        </div>
        <div style={{ fontSize: "30px", fontWeight: 900, marginTop: "6px" }}>
          {stats.total}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {sortedReasons.map(([reason, count]) => (
          <div
            key={reason}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "12px 14px",
              borderRadius: "14px",
              background: "rgba(255,255,255,0.03)",
            }}
          >
            <span style={{ fontWeight: 700, textTransform: "capitalize" }}>{reason}</span>
            <span style={{ fontWeight: 900 }}>{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
type Props = {
  flaggedCount: number;
  overtimeHours: number;
  team: string;
  lastActive: string;
};

type StatProps = {
  label: string;
  value: string | number;
};

function Stat({ label, value }: StatProps) {
  return (
    <div
      style={{
        flex: 1,
        minWidth: "120px",
        padding: "12px 14px",
        borderRadius: "16px",
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      <div
        style={{
          fontSize: "10px",
          fontWeight: 900,
          letterSpacing: "1px",
          textTransform: "uppercase",
          opacity: 0.45,
          marginBottom: "6px",
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: "15px", fontWeight: 800, color: "#fff" }}>{value}</div>
    </div>
  );
}

export default function EmployeeStatsRow({
  flaggedCount,
  overtimeHours,
  team,
  lastActive,
}: Props) {
  return (
    <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
      <Stat label="Flagged" value={flaggedCount} />
      <Stat label="Overtime" value={`${overtimeHours}h`} />
      <Stat label="Team" value={team} />
      <Stat label="Last active" value={lastActive} />
    </div>
  );
}
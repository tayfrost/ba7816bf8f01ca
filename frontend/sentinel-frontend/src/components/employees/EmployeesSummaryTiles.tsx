type Props = {
  totalEmployees: number
  highRiskEmployees: number
  flaggedMessages: number
  avgRisk: number
}

function Tile({ label, value }: { label: string; value: string | number }) {
  return (
    <div
      style={{
        flex: 1,
        minWidth: "180px",
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "24px",
        padding: "24px",
      }}
    >
      <div
        style={{
          fontSize: "11px",
          fontWeight: 900,
          letterSpacing: "1px",
          opacity: 0.4,
          textTransform: "uppercase",
          marginBottom: "8px",
        }}
      >
        {label}
      </div>

      <div
        style={{
          fontSize: "30px",
          fontWeight: 900,
          color: "#fff",
        }}
      >
        {value}
      </div>
    </div>
  )
}

export default function EmployeesSummaryTiles({
  totalEmployees,
  highRiskEmployees,
  flaggedMessages,
  avgRisk,
}: Props) {
  return (
    <div
      style={{
        display: "flex",
        gap: "20px",
        marginBottom: "40px",
        flexWrap: "wrap",
      }}
    >
      <Tile label="Employees monitored" value={totalEmployees} />
      <Tile label="High risk employees" value={highRiskEmployees} />
      <Tile label="Flagged messages" value={flaggedMessages} />
      <Tile label="Average risk" value={`${avgRisk}%`} />
    </div>
  )
}
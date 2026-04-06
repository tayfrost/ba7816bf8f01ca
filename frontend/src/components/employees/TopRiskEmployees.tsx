import RiskBadge from "./RiskBadge"

type Employee = {
  id: string
  fullName: string
  role: string
  riskScore: number
}

type Props = {
  employees: Employee[]
}

export default function TopRiskEmployees({ employees }: Props) {
  const top = [...employees]
    .sort((a, b) => b.riskScore - a.riskScore)
    .slice(0, 5)

  return (
    <div
      style={{
        marginBottom: "40px",
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "30px",
        padding: "28px",
      }}
    >
      <h3
        style={{
          margin: "0 0 20px 0",
          fontWeight: 900,
          letterSpacing: "1px",
        }}
      >
        Top Risk Employees
      </h3>

      <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        {top.map((emp) => (
          <div
            key={emp.id}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "12px 16px",
              borderRadius: "14px",
              background: "rgba(255,255,255,0.02)",
            }}
          >
            <div>
              <div style={{ fontWeight: 800 }}>{emp.fullName}</div>
              <div style={{ opacity: 0.5, fontSize: "12px" }}>{emp.role}</div>
            </div>

            <RiskBadge score={emp.riskScore} />
          </div>
        ))}
      </div>
    </div>
  )
}
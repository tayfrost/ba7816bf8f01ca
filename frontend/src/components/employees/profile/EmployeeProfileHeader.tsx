import type { Employee } from "../../../types/employees";
import EmployeeSources from "../EmployeeSources";
import RiskBadge from "../RiskBadge";
import SimpleLineChart from "../../SimpleLineChart";

type Props = {
  employee: Employee;
};

export default function EmployeeProfileHeader({ employee }: Props) {
  return (
    <div
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "32px",
        padding: "32px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: "20px",
          alignItems: "flex-start",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: "34px", fontWeight: 900 }}>
            {employee.fullName}
          </h1>
          <p style={{ margin: "10px 0 0 0", opacity: 0.65, fontWeight: 700 }}>
            {employee.role}
          </p>
          <p style={{ margin: "8px 0 0 0", opacity: 0.45 }}>
            {employee.email}
          </p>
          <p style={{ margin: "8px 0 0 0", opacity: 0.45 }}>
            Team: {employee.team}
          </p>
        </div>

        <RiskBadge score={employee.riskScore} />
      </div>

      <div style={{ marginTop: "24px" }}>
        <EmployeeSources sources={employee.source} />
      </div>

      <div style={{ marginTop: "28px", width: "100%", overflow: "hidden" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
          <span style={{ fontSize: "11px", fontWeight: 900, letterSpacing: "1.5px", textTransform: "uppercase", opacity: 0.5 }}>
            Weighted Risk Trend (30-day)
          </span>
          <div
            title="Combines incident severity by category using weighted scoring: Suicidal ideation ×10, Harassment ×8, Depression ×7, Burnout ×5, Stress ×3. Log-dampened so repeat incidents in one day don't dominate. Scale: 0–100."
            style={{
              width: "16px",
              height: "16px",
              borderRadius: "50%",
              background: "rgba(255,255,255,0.1)",
              border: "1px solid rgba(255,255,255,0.2)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "10px",
              fontWeight: 900,
              cursor: "help",
              opacity: 0.6,
              flexShrink: 0,
            }}
          >
            i
          </div>
        </div>
        <SimpleLineChart points={employee.trend} width={520} height={220} maxValue={100} />
      </div>
    </div>
  );
}
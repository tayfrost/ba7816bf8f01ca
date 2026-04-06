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

      <div style={{ marginTop: "28px" }}>
        <SimpleLineChart points={employee.trend} width={700} height={260} />
      </div>
    </div>
  );
}
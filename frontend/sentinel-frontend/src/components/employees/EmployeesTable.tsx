import type { Employee } from "../../types/employees";
import RiskBadge from "./RiskBadge";
import RiskProgressBar from "./RiskProgressBar";
import EmployeeSources from "./EmployeeSources";

type Props = {
  employees: Employee[];
  onSelectEmployee: (employeeId: string) => void;
};

export default function EmployeesTable({ employees, onSelectEmployee }: Props) {
  return (
    <div
      style={{
        marginTop: "30px",
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "30px",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.5fr 1fr 1fr 1.2fr 0.8fr 0.8fr",
          gap: "16px",
          padding: "18px 24px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          fontSize: "11px",
          fontWeight: 900,
          letterSpacing: "1px",
          textTransform: "uppercase",
          opacity: 0.45,
        }}
      >
        <div>Employee</div>
        <div>Team</div>
        <div>Sources</div>
        <div>Risk Trend</div>
        <div>Flagged</div>
        <div>Status</div>
      </div>

      <div style={{ display: "flex", flexDirection: "column" }}>
        {employees.map((employee, index) => (
          <div
            key={employee.id}
            onClick={() => onSelectEmployee(employee.id)}
            style={{
              display: "grid",
              gridTemplateColumns: "1.5fr 1fr 1fr 1.2fr 0.8fr 0.8fr",
              gap: "16px",
              padding: "18px 24px",
              alignItems: "center",
              borderBottom:
                index === employees.length - 1
                  ? "none"
                  : "1px solid rgba(255,255,255,0.05)",
              cursor: "pointer",
              transition: "background 0.2s ease",
              background: "rgba(255,255,255,0.01)",
            }}
          >
            <div>
              <div style={{ fontWeight: 800, color: "#fff" }}>{employee.fullName}</div>
              <div style={{ fontSize: "12px", opacity: 0.55 }}>{employee.role}</div>
            </div>

            <div style={{ fontSize: "13px", fontWeight: 700 }}>{employee.team}</div>

            <div>
              <EmployeeSources sources={employee.source} />
            </div>

            <div>
              <RiskProgressBar value={employee.riskScore} />
            </div>

            <div style={{ fontSize: "14px", fontWeight: 800 }}>{employee.flaggedCount}</div>

            <div>
              <RiskBadge score={employee.riskScore} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
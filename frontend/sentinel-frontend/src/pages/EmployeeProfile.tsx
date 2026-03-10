import { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useOnboarding } from "../state/onboarding";
import SidebarLink from "../components/SidebarLink";
import { MOCK_EMPLOYEES } from "../state/employeesMock";
import EmployeeSources from "../components/employees/EmployeeSources";
import RiskBadge from "../components/employees/RiskBadge";
import SimpleLineChart from "../components/SimpleLineChart";

const BRAND_ORANGE = "var(--color-top)";

export default function EmployeeProfile() {
  const { employeeId } = useParams();
  const navigate = useNavigate();
  const { reset } = useOnboarding();

  const employee = useMemo(
    () => MOCK_EMPLOYEES.find((e) => e.id === employeeId),
    [employeeId]
  );

  if (!employee) {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: "linear-gradient(to bottom, #20022bfd, #1a011d)",
          color: "white",
          display: "grid",
          placeItems: "center",
          fontFamily: "'Outfit', 'Inter', sans-serif",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <h1>Employee not found</h1>
          <button
            onClick={() => navigate("/employees")}
            style={{
              marginTop: "20px",
              padding: "12px 18px",
              borderRadius: "12px",
              border: "none",
              background: BRAND_ORANGE,
              color: "#1a011d",
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            Back to Employees
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        background: "linear-gradient(to bottom, #20022bfd, #1a011d)",
        minHeight: "100vh",
        color: "#ffffff",
        display: "flex",
        fontFamily: "'Outfit', 'Inter', sans-serif",
        overflow: "hidden",
      }}
    >
      <aside
        style={{
          width: "280px",
          height: "100vh",
          background: "rgba(0, 0, 0, 0.4)",
          backdropFilter: "blur(30px)",
          borderRight: "1px solid rgba(255, 255, 255, 0.05)",
          display: "flex",
          flexDirection: "column",
          padding: "40px 20px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "50px" }}>
          <img src="/logo-text.png" alt="SentinelAI" style={{ height: "30px", marginBottom: "40px", paddingLeft: "20px" }} />
        </div>

        <nav style={{ flexGrow: 1 }}>
          <SidebarLink to="/dashboard" label="Dashboard" />
          <SidebarLink to="/employees" label="Employees" />
          <SidebarLink to="/connect-accounts" label="Connected Accounts" />
          <SidebarLink to="/usage" label="Usage Guide" />
          <SidebarLink to="/settings" label="Account Settings" />
        </nav>

        <button
          onClick={reset}
          style={{
            background: "transparent",
            border: "1px solid rgba(255,255,255,0.1)",
            color: "rgba(255,255,255,0.4)",
            padding: "10px",
            borderRadius: "8px",
            cursor: "pointer",
            fontSize: "11px",
            fontWeight: "bold",
          }}
        >
          RESET SYSTEM
        </button>
      </aside>

      <main style={{ flexGrow: 1, padding: "50px 60px", overflowY: "auto", height: "100vh" }}>
        <button
          onClick={() => navigate("/employees")}
          style={{
            marginBottom: "24px",
            background: "none",
            border: "none",
            color: BRAND_ORANGE,
            fontWeight: 800,
            cursor: "pointer",
            letterSpacing: "1px",
          }}
        >
          ← BACK TO EMPLOYEES
        </button>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1.2fr 0.8fr",
            gap: "30px",
            marginBottom: "30px",
          }}
        >
          <div
            style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "32px",
              padding: "32px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: "20px", alignItems: "flex-start" }}>
              <div>
                <h1 style={{ margin: 0, fontSize: "34px", fontWeight: 900 }}>{employee.fullName}</h1>
                <p style={{ margin: "10px 0 0 0", opacity: 0.65, fontWeight: 700 }}>{employee.role}</p>
                <p style={{ margin: "8px 0 0 0", opacity: 0.45 }}>{employee.email}</p>
                <p style={{ margin: "8px 0 0 0", opacity: 0.45 }}>Team: {employee.team}</p>
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

          <div
            style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "32px",
              padding: "32px",
              display: "flex",
              flexDirection: "column",
              gap: "18px",
            }}
          >
            <h3 style={{ margin: 0, color: BRAND_ORANGE, letterSpacing: "1px" }}>Workload Summary</h3>

            <div style={{ padding: "16px", borderRadius: "18px", background: "rgba(255,255,255,0.04)" }}>
              <div style={{ opacity: 0.5, fontSize: "12px", marginBottom: "6px" }}>Flagged messages</div>
              <div style={{ fontSize: "28px", fontWeight: 900 }}>{employee.flaggedCount}</div>
            </div>

            <div style={{ padding: "16px", borderRadius: "18px", background: "rgba(255,255,255,0.04)" }}>
              <div style={{ opacity: 0.5, fontSize: "12px", marginBottom: "6px" }}>Overtime hours</div>
              <div style={{ fontSize: "28px", fontWeight: 900 }}>{employee.overtimeHours}h</div>
            </div>

            <div style={{ padding: "16px", borderRadius: "18px", background: "rgba(255,255,255,0.04)" }}>
              <div style={{ opacity: 0.5, fontSize: "12px", marginBottom: "6px" }}>Last active</div>
              <div style={{ fontSize: "20px", fontWeight: 800 }}>{employee.lastActive}</div>
            </div>
          </div>
        </div>

        <div
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: "32px",
            padding: "32px",
          }}
        >
          <h3 style={{ marginTop: 0, color: BRAND_ORANGE, letterSpacing: "1px" }}>Recent Incident Timeline</h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {[
              "Burnout language spike detected in team communication.",
              "Elevated after-hours activity observed across 3 consecutive days.",
              "Stress-related language flagged in internal message thread.",
              "Sharp increase in flagged message severity during current week.",
            ].map((item, idx) => (
              <div
                key={idx}
                style={{
                  padding: "18px 20px",
                  borderRadius: "18px",
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.05)",
                }}
              >
                <div style={{ fontSize: "12px", opacity: 0.45, marginBottom: "6px" }}>
                  Incident #{idx + 1}
                </div>
                <div style={{ fontWeight: 700 }}>{item}</div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
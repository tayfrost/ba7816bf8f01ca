import { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useOnboarding } from "../state/onboarding";
import SidebarLink from "../components/SidebarLink";
import { useEmployeesData } from "../hooks/useEmployeesData";
import EmployeeProfileHeader from "../components/employees/profile/EmployeeProfileHeader";
import EmployeeWorkloadSummary from "../components/employees/profile/EmployeeWorkloadSummary";
import EmployeeIncidentTimeline from "../components/employees/profile/EmployeeIncidentTimeline";

const BRAND_ORANGE = "var(--color-top)";

export default function EmployeeProfile() {
  const { employeeId } = useParams();
  const navigate = useNavigate();
  const { reset } = useOnboarding();

  const { employees, status, error } = useEmployeesData();

  const employee = useMemo(
    () => employees.find((e) => e.id === employeeId),
    [employees, employeeId]
  );

  if (status === "loading") {
    return (
      <div
        className="px-6 text-center" // Adds padding and centers text for mobile
        style={{
          minHeight: "100vh",
          background: "linear-gradient(to bottom, #20022bfd, #1a011d)",
          color: "white",
          display: "grid",
          placeItems: "center",
          fontFamily: "'Outfit', 'Inter', sans-serif",
        }}
      >
        Loading employee profile...
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="px-6 text-center" // Adds padding and centers text for mobile
        style={{
          minHeight: "100vh",
          background: "linear-gradient(to bottom, #20022bfd, #1a011d)",
          color: "white",
          display: "grid",
          placeItems: "center",
          fontFamily: "'Outfit', 'Inter', sans-serif",
        }}
      >
        Failed to load employee profile.
      </div>
    );
  }

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

  const incidents = [
    "Burnout language spike detected in team communication.",
    "Elevated after-hours activity observed across 3 consecutive days.",
    "Stress-related language flagged in internal message thread.",
    "Sharp increase in flagged message severity during current week.",
  ];

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
        className="hidden lg:flex flex-col w-[280px] h-screen sticky top-0 p-10 shrink-0"
        style={{
          background: "rgba(0, 0, 0, 0.4)",
          backdropFilter: "blur(30px)",
          borderRight: "1px solid rgba(255, 255, 255, 0.05)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "50px" }}>
          <img src="/logo-text.png" alt="SentinelAI" style={{ height: "30px", marginBottom: "40px", paddingLeft: "20px", filter: "brightness(0) invert(1)" }} />
        </div>

        <nav style={{ flexGrow: 1 }}>
          <SidebarLink to="/dashboard" label="Dashboard" />
          <SidebarLink to="/employees" label="Employees" />
          <SidebarLink to="/settings" label="Account Settings" />
        </nav>

        <button
          onClick={() => { reset(); navigate("/login"); }}
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

      <main className="flex-grow min-w-0 p-4 md:p-10 lg:p-[60px] overflow-y-auto h-screen">
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

        <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_0.8fr] gap-6 lg:gap-8 mb-8">
          <EmployeeProfileHeader employee={employee} />

          <EmployeeWorkloadSummary employee={employee} />
        </div>

        <EmployeeIncidentTimeline incidents={incidents} />

        <div className="h-24 lg:hidden" />
      </main>

      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 px-6 py-4 flex justify-around items-center" 
        style={{
          background: "rgba(20, 1, 22, 0.9)",
          backdropFilter: "blur(20px)",
          borderTop: "1px solid rgba(255, 255, 255, 0.1)",
        }}
        >
        <SidebarLink to="/dashboard" label="Home" end />
        <SidebarLink to="/employees" label="Employees" />
        <SidebarLink to="/settings" label="Settings" />
      </nav>  

    </div>
  );
}
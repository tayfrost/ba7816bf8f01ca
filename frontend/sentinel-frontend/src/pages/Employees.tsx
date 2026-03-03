import { useMemo, useState } from "react";
import { useOnboarding } from "../state/onboarding";
import { countConnected } from "../state/integrationRules";
import SidebarLink from "../components/SidebarLink";
import EmployeeCard from "../components/EmployeeCard";

const BRAND_ORANGE = "var(--color-top)"; 
const BRAND_DEEP = "var(--color-brand-deep)";

// Data derived from the "Flagged incidents" backend logic
const MOCK_EMPLOYEES = [
  { id: "u1", name: "Sarah Jenkins", role: "Senior Engineer", risk: 82, flagged: 14, overtime: 12 },
  { id: "u2", name: "Marcus Chen", role: "Product Manager", risk: 15, flagged: 2, overtime: 4 },
  { id: "u3", name: "Elena Rodriguez", role: "UX Designer", risk: 45, flagged: 7, overtime: 9 },
  { id: "u4", name: "David Kim", role: "DevOps", risk: 91, flagged: 28, overtime: 22 },
];

export default function Employees() {
  const { signup, plan, integrations, reset } = useOnboarding();
  const [searchTerm, setSearchTerm] = useState("");

  const connectedCount = useMemo(() => countConnected(integrations), [integrations]);

  const riskScore = useMemo(() => Math.min(100, 35 + connectedCount * 20), [connectedCount]);

  const filteredEmployees = useMemo(() => {
    return MOCK_EMPLOYEES.filter(emp => 
      emp.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      emp.role.toLowerCase().includes(searchTerm.toLowerCase())
    ).sort((a, b) => b.risk - a.risk);
  }, [searchTerm]);

  return (
    <div style={{
      background: "linear-gradient(to bottom, #20022bfd, #1a011d)",
      minHeight: "100vh",
      color: "#ffffff",
      display: "flex",
      fontFamily: "'Outfit', 'Inter', sans-serif",
      overflow: "hidden"
    }}>
      
      {/* SIDEBAR */}
      <aside style={{
        width: "280px",
        height: "100vh",
        background: "rgba(0, 0, 0, 0.4)",
        backdropFilter: "blur(30px)",
        borderRight: "1px solid rgba(255, 255, 255, 0.05)",
        display: "flex",
        flexDirection: "column",
        padding: "40px 20px"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "50px" }}>
          <img src="/logo-text.png" alt="SentinelAI" style={{ height: "30px", marginBottom: "40px", paddingLeft: "20px" }} />
        </div>

        <nav style={{ flexGrow: 1 }}>
          <SidebarLink to="/dashboard" label="Dashboard" end />
          <SidebarLink to="/employees" label="Employees" />
          <SidebarLink to="/connect-accounts" label="Connected Accounts" />
          <SidebarLink to="/usage" label="Usage Guide" />
          <SidebarLink to="/settings" label="Account Settings" />
        </nav>

        <button onClick={reset} style={{ 
          background: "transparent", border: "1px solid rgba(255,255,255,0.1)", 
          color: "rgba(255,255,255,0.4)", padding: "10px", borderRadius: "8px", cursor: "pointer", fontSize: "11px", fontWeight: "bold"
        }}>
          RESET SYSTEM
        </button>
      </aside>

      {/* MAIN SECTION */}
      <main style={{ flexGrow: 1, padding: "50px 60px", overflowY: "auto", height: "100vh" }}>
 
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "50px" }}>
          <div>
            <h1 style={{ fontSize: "38px", fontWeight: "900", margin: 0, letterSpacing: "-1px" }}>
              Welcome, <span style={{ color: BRAND_ORANGE, textShadow: `0 0 20px rgba(227, 141, 38, 0.3)` }}>{signup?.companyName}</span>
            </h1>
            <p style={{ opacity: 0.5, marginTop: "10px", fontWeight: "700", textTransform: "uppercase", fontSize: "12px", letterSpacing: "1px" }}>
              {plan} MEMBER • {connectedCount} ACTIVE SOURCES
            </p>
          </div>

          <div style={{
            width: "140px",
            height: "140px",
            background: `linear-gradient(135deg, rgba(227, 141, 38, 0.3) 0%, ${BRAND_DEEP} 100%)`,
            border: `2px solid ${BRAND_ORANGE}`,
            borderRadius: "32px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            boxShadow: `0 0 40px rgba(227, 141, 38, 0.2)`,
            position: "relative",
            overflow: "hidden"
          }}>
            <div style={{ position: "absolute", top: -20, left: -20, width: 70, height: 70, background: BRAND_ORANGE, filter: "blur(45px)", opacity: 0.4 }} />
            <span style={{ fontSize: "12px", fontWeight: "900", color: BRAND_ORANGE, letterSpacing: "2px", marginBottom: "4px", zIndex: 1 }}>RISK</span>
            <span style={{ fontSize: "48px", fontWeight: "900", color: "#fff", zIndex: 1 }}>{riskScore}%</span>
          </div>
        </header>

        <section style={{ marginBottom: "40px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ 
            display: "flex", 
            gap: "15px", 
            background: "rgba(0,0,0,0.5)", 
            padding: "10px 20px", 
            borderRadius: "50px", 
            border: "1px solid rgba(255,255,255,0.08)",
            width: "400px"
          }}>
             <span style={{ color: BRAND_ORANGE, fontWeight: "900", fontSize: "12px" }}>SEARCH</span>
             <input 
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Filter by name or role..."
              style={{
                background: "transparent",
                border: "none",
                color: "white",
                outline: "none",
                fontSize: "13px",
                width: "100%",
                fontWeight: "600"
              }}
             />
          </div>
        </section>

        {/* EMPLOYEE DATA GRID */}
        <div style={{ 
          display: "grid", 
          gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", 
          gap: "30px" 
        }}>
          {filteredEmployees.map(emp => (
            <div key={emp.id} style={{
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: "35px",
              padding: "30px",
              backdropFilter: "blur(20px)"
            }}>
              <EmployeeCard 
                fullName={emp.name}
                role={emp.role}
                riskScore={emp.risk}
                flaggedCount={emp.flagged}
                overtimeHours={emp.overtime}
              />
            </div>
          ))}
        </div>

        {filteredEmployees.length === 0 && (
          <div style={{ textAlign: "center", marginTop: "100px", opacity: 0.2 }}>
            <h2 style={{ fontSize: "20px", fontWeight: "900", letterSpacing: "2px" }}>NO DIRECTORY MATCHES</h2>
          </div>
        )}

      </main>
    </div>
  );
}
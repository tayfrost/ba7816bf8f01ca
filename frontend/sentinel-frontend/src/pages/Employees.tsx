import { useMemo, useState } from "react";
import { useOnboarding } from "../state/onboarding";
import { countConnected } from "../state/integrationRules";
import SidebarLink from "../components/SidebarLink";
import EmployeeCard from "../components/EmployeeCard";
import { MOCK_EMPLOYEES } from "../state/employeesMock";
import { useEmployeesData } from "../hooks/useEmployeesData";
import EmployeesFilters from "../components/employees/EmployeesFilters";
import RiskBadge from "../components/employees/RiskBadge";
import EmployeesSummaryTiles from "../components/employees/EmployeesSummaryTiles"
import TopRiskEmployees from "../components/employees/TopRiskEmployees"
import EmptyEmployees from "../components/employees/EmptyEmployees"
import EmployeesTable from "../components/employees/EmployeesTable";

const BRAND_ORANGE = "var(--color-top)"; 
const BRAND_DEEP = "var(--color-brand-deep)";
const [directoryView, setDirectoryView] = useState<"cards" | "table">("cards");

export default function Employees() {
  const { signup, plan, integrations, reset } = useOnboarding();

  const connectedCount = useMemo(() => countConnected(integrations), [integrations]);

  const riskScore = useMemo(() => Math.min(100, 35 + connectedCount * 20), [connectedCount]);

  const {
    employees,
    stats,
    status,
    error,
    searchTerm,
    setSearchTerm,
    riskFilter,
    setRiskFilter,
    sourceFilter,
    setSourceFilter,
    sortBy,
    setSortBy,
  } = useEmployeesData();

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
            <p style={{ opacity: 0.35, marginTop: "8px", fontWeight: "700", fontSize: "11px", letterSpacing: "1px" }}>
              {stats.total} EMPLOYEES • {stats.watchlist} WATCHLIST • {stats.critical} CRITICAL
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

        <EmployeesSummaryTiles
        totalEmployees={stats.total}
        highRiskEmployees={stats.high}
        flaggedMessages={stats.flagged}
        avgRisk={stats.avgRisk}
        />

        {status === "loading" && (
          <div style={{ marginBottom: 20, opacity: 0.75, fontWeight: 700 }}>
            Loading employees...
          </div>
        )}
        
        {status === "error" && error && (
          <div style={{ marginBottom: 20, color: BRAND_ORANGE, fontWeight: 800 }}>
            {error}
          </div>
        )}

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

        <div style={{ display: "flex", gap: "12px", marginBottom: "20px" }}>
          <button
            onClick={() => setDirectoryView("cards")}
            style={{
              padding: "10px 16px",
              borderRadius: "14px",
              border: "1px solid rgba(255,255,255,0.08)",
              background: directoryView === "cards" ? "rgba(227,141,38,0.2)" : "rgba(255,255,255,0.03)",
              color: directoryView === "cards" ? BRAND_ORANGE : "rgba(255,255,255,0.6)",
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            Card View
          </button>
          
          <button
            onClick={() => setDirectoryView("table")}
            style={{
              padding: "10px 16px",
              borderRadius: "14px",
              border: "1px solid rgba(255,255,255,0.08)",
              background: directoryView === "table" ? "rgba(227,141,38,0.2)" : "rgba(255,255,255,0.03)",
              color: directoryView === "table" ? BRAND_ORANGE : "rgba(255,255,255,0.6)",
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            Table View
          </button>
        </div>

        <EmployeesFilters
          riskFilter={riskFilter}
          setRiskFilter={setRiskFilter}
          sourceFilter={sourceFilter}
          setSourceFilter={setSourceFilter}
          sortBy={sortBy}
          setSortBy={setSortBy}
        />

        <TopRiskEmployees employees={employees} />

        {/* EMPLOYEE DATA GRID */}
        {directoryView === "cards" ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
              gap: "30px",
            }}
          >
            {employees.map((emp) => (
              <div
                key={emp.id}
                style={{
                  background: "rgba(255, 255, 255, 0.03)",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                  borderRadius: "35px",
                  padding: "30px",
                  backdropFilter: "blur(20px)",
                }}
              >
                <div style={{ marginBottom: "10px" }}>
                  <RiskBadge score={emp.riskScore} />
                </div>
                
                <EmployeeCard
                  fullName={emp.fullName}
                  role={emp.role}
                  email={emp.email}
                  team={emp.team}
                  riskScore={emp.riskScore}
                  flaggedCount={emp.flaggedCount}
                  overtimeHours={emp.overtimeHours}
                  lastActive={emp.lastActive}
                  sources={emp.source}
                  trend={emp.trend}
                />
              </div>
            ))}
          </div>
        ) : (
          <EmployeesTable employees={employees} />
        )}

        {employees.length === 0 && <EmptyEmployees />}

      </main>
    </div>
  );
}
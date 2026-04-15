import { useEffect, useMemo, useState } from "react";
import { useOnboarding } from "../state/onboarding";
import { countConnected } from "../state/integrationRules";
import { useCompany } from "../hooks/useCompany";
import SidebarLink from "../components/SidebarLink";
import EmployeeCard from "../components/EmployeeCard";
import { useEmployeesData } from "../hooks/useEmployeesData";
import EmployeesFilters from "../components/employees/EmployeesFilters";
import RiskBadge from "../components/employees/RiskBadge";
import EmployeesSummaryTiles from "../components/employees/EmployeesSummaryTiles"
import TopRiskEmployees from "../components/employees/TopRiskEmployees"
import EmptyEmployees from "../components/employees/EmptyEmployees"
import EmployeesTable from "../components/employees/EmployeesTable";
import { useNavigate } from "react-router-dom";

const BRAND_ORANGE = "var(--color-top)"; 
const BRAND_DEEP = "var(--color-brand-deep)";

export default function Employees() {
  const { plan, integrations } = useOnboarding();
  const { company } = useCompany();
  const companyName = company?.company_name || "";

  const PAGE_SIZE = 10;
  const [directoryView, setDirectoryView] = useState<"cards" | "table">("table");
  const [page, setPage] = useState(1);
  const navigate = useNavigate();

  const connectedCount = useMemo(() => countConnected(integrations), [integrations]);

  const riskScore = useMemo(() => Math.min(100, 35 + connectedCount * 20), [connectedCount]);

  const {
    employees,
    stats,
    status,
    searchTerm,
    setSearchTerm,
    riskFilter,
    setRiskFilter,
    sourceFilter,
    setSourceFilter,
    sortBy,
    setSortBy,
  } = useEmployeesData();

  const handleSearchTermChange = (value: string) => {
    setPage(1);
    setSearchTerm(value);
  };

  const handleRiskFilterChange = (value: typeof riskFilter) => {
    setPage(1);
    setRiskFilter(value);
  };

  const handleSourceFilterChange = (value: typeof sourceFilter) => {
    setPage(1);
    setSourceFilter(value);
  };

  const handleSortByChange = (value: typeof sortBy) => {
    setPage(1);
    setSortBy(value);
  };

  // Redirect on data load failure
  useEffect(() => {
    if (status === "error") navigate("/error", { replace: true });
  }, [status, navigate]);

  const totalPages = Math.max(1, Math.ceil(employees.length / PAGE_SIZE));
  const pagedEmployees = employees.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

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
          <SidebarLink to="/dashboard" label="Dashboard" end />
          <SidebarLink to="/employees" label="Employees" />
          <SidebarLink to="/settings" label="Account Settings" />
        </nav>

      </aside>

      {/* MAIN SECTION */}
      <main className="flex-grow p-4 md:p-10 lg:p-[60px] overflow-y-auto h-screen">
 
        <header className="flex flex-col lg:flex-row lg:items-center justify-between gap-8 mb-12">
          <div>
            <h1 style={{ fontSize: "38px", fontWeight: "900", margin: 0, letterSpacing: "-1px" }}>
              Welcome, <span style={{ color: BRAND_ORANGE, textShadow: `0 0 20px rgba(227, 141, 38, 0.3)` }}>{companyName}</span>
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

        <section className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-10">
          <div className="flex gap-[15px] bg-black/50 px-5 py-2.5 rounded-full border border-white/10 w-full max-w-[400px]">
             <span style={{ color: BRAND_ORANGE, fontWeight: "900", fontSize: "12px" }}>SEARCH</span>
             <input 
              type="text"
              value={searchTerm}
              onChange={(e) => handleSearchTermChange(e.target.value)}
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

          <div style={{ 
            display: "flex", 
            gap: "30px", 
            background: "rgba(255, 255, 255, 0)", 
            padding: "10px 30px", 
            borderRadius: "50px", 
            border: "1px solid rgba(255, 255, 255, 0)" 
          }}>
            <button
              onClick={() => setDirectoryView("cards")}
              style={{
                background: "none",
                border: "none",
                color: directoryView === "cards" ? BRAND_ORANGE : "rgba(255,255,255,0.3)",
                fontSize: "12px",
                fontWeight: "900",
                letterSpacing: "1px",
                cursor: "pointer",
                transition: "all 0.2s"
              }}
            >
              CARDS
            </button>
            <button
              onClick={() => setDirectoryView("table")}
              style={{
                background: "none",
                border: "none",
                color: directoryView === "table" ? BRAND_ORANGE : "rgba(255,255,255,0.3)",
                fontSize: "12px",
                fontWeight: "900",
                letterSpacing: "1px",
                cursor: "pointer",
                transition: "all 0.2s"
              }}
            >
              TABLE
            </button>
          </div>
        </section>

        <EmployeesFilters
          riskFilter={riskFilter}
          setRiskFilter={handleRiskFilterChange}
          sourceFilter={sourceFilter}
          setSourceFilter={handleSourceFilterChange}
          sortBy={sortBy}
          setSortBy={handleSortByChange}
        />

        <TopRiskEmployees
          employees={employees}
          onSelect={(id) => navigate(`/employees/${id}`)}
        />

        {/* EMPLOYEE DATA GRID */}
        {directoryView === "cards" ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {pagedEmployees.map((emp) => (
              <div
                key={emp.id}
                onClick={() => navigate(`/employees/${emp.id}`)}
                style={{
                  background: "rgba(255, 255, 255, 0.03)",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                  borderRadius: "35px",
                  padding: "30px",
                  backdropFilter: "blur(20px)",
                  cursor: "pointer",
                  overflow: "hidden",
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
          <EmployeesTable
            employees={pagedEmployees}
            onSelectEmployee={(employeeId) => navigate(`/employees/${employeeId}`)}
          />
        )}

        {employees.length === 0 && <EmptyEmployees />}

        {/* Pagination controls */}
        {employees.length > PAGE_SIZE && (
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "20px", marginTop: "24px" }}>
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              style={{
                padding: "10px 22px", borderRadius: "12px", fontWeight: 800, fontSize: "12px", cursor: page === 1 ? "default" : "pointer",
                background: page === 1 ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.08)",
                border: "1px solid rgba(255,255,255,0.1)", color: page === 1 ? "rgba(255,255,255,0.3)" : "#fff",
              }}
            >
              ← Prev
            </button>
            <span style={{ fontSize: "12px", fontWeight: 800, opacity: 0.6 }}>
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              style={{
                padding: "10px 22px", borderRadius: "12px", fontWeight: 800, fontSize: "12px", cursor: page === totalPages ? "default" : "pointer",
                background: page === totalPages ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.08)",
                border: "1px solid rgba(255,255,255,0.1)", color: page === totalPages ? "rgba(255,255,255,0.3)" : "#fff",
              }}
            >
              Next →
            </button>
          </div>
        )}

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
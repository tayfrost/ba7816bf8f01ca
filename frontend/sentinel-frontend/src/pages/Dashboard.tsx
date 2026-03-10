import { useMemo, useState } from "react";
import { useOnboarding } from "../state/onboarding";
import { countConnected } from "../state/integrationRules";
import { computeRange } from "../state/timeRange";
import type { RangePreset } from "../state/timeRange";
import SimpleLineChart from "../components/SimpleLineChart";
import { useDashboardData } from "../hooks/useDashboardData";
import SidebarLink from "../components/SidebarLink";
import DashboardHeader from "../components/dashboard/DashboardHeader";
import RangeSelector from "../components/dashboard/RangeSelector";
import ViewModeToggle from "../components/dashboard/ViewModeToggle";
import CustomDateRange from "../components/dashboard/CustomDateRange";

const BRAND_ORANGE = "var(--color-top)"; 

export default function Dashboard() {
  const { signup, plan, integrations, reset } = useOnboarding();

  const [preset, setPreset] = useState<RangePreset>("week");
  const [customStart, setCustomStart] = useState("2026-01-01");
  const [customEnd, setCustomEnd] = useState("2026-02-20");
  
  const [viewMode, setViewMode] = useState<"focused" | "grid">("focused");
  const [activeCatalogIndex, setActiveCatalogIndex] = useState(0);

  const range = useMemo(() => {
    if (preset === "custom") return computeRange("custom", { start: customStart, end: customEnd });
    return computeRange(preset);
  }, [preset, customStart, customEnd]);

  const { status, error, series: metricSeries, isMock } = useDashboardData(range);
  const connectedCount = useMemo(() => countConnected(integrations), [integrations]);
  const riskScore = useMemo(() => Math.min(100, 35 + connectedCount * 20), [connectedCount]);

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
        
        <DashboardHeader
          companyName={signup?.companyName}
          plan={plan}
          connectedCount={connectedCount}
          riskScore={riskScore}
        />

        <section
          style={{
            marginBottom: "40px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <RangeSelector preset={preset} setPreset={setPreset} />
          <ViewModeToggle viewMode={viewMode} setViewMode={setViewMode} />
        </section>

        {preset === "custom" && (
          <CustomDateRange
            customStart={customStart}
            customEnd={customEnd}
            setCustomStart={setCustomStart}
            setCustomEnd={setCustomEnd}
          />
        )}

        {status === "loading" && (
          <div style={{ marginBottom: 18, opacity: 0.8 }}>
            Loading metrics…
          </div>
        )}
        
        {status === "error" && error && (
          <div style={{ marginBottom: 18, opacity: 0.9, color: BRAND_ORANGE, fontWeight: 800 }}>
            {error}
          </div>
        )}

        {isMock && (
          <div style={{ marginBottom: 18, opacity: 0.9, color: BRAND_ORANGE, fontWeight: 800 }}>
            Showing mock data (mock mode enabled)
          </div>
        )}

        {viewMode === "focused" ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "30px" }}>
            <div style={{ 
              background: "rgba(255, 255, 255, 0.03)", 
              padding: "50px", 
              borderRadius: "50px", 
              border: "1px solid rgba(255,255,255,0.1)",
              boxShadow: "0 20px 50px rgba(0,0,0,0.3)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center"
            }}>
              <div style={{ display: "flex", gap: "12px", marginBottom: "40px", flexWrap: "wrap", justifyContent: "center" }}>
                {metricSeries.map((s, idx) => (
                  <button 
                    key={s.key} 
                    onClick={() => setActiveCatalogIndex(idx)}
                    style={{
                      padding: "10px 20px",
                      borderRadius: "15px",
                      border: activeCatalogIndex === idx ? `1px solid ${BRAND_ORANGE}` : "1px solid rgba(255,255,255,0.1)",
                      background: activeCatalogIndex === idx ? `rgba(227, 141, 38, 0.2)` : "rgba(255,255,255,0.02)",
                      color: activeCatalogIndex === idx ? BRAND_ORANGE : "rgba(255,255,255,0.5)",
                      fontWeight: "800",
                      cursor: "pointer",
                      fontSize: "12px",
                      transition: "all 0.2s"
                    }}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
       
              <SimpleLineChart points={metricSeries[activeCatalogIndex]?.points || []} width={850} height={400} />
            </div>

            <div style={{ display: "flex", gap: "20px", overflowX: "auto", paddingBottom: "20px", marginTop: "20px" }}>
              {metricSeries.filter((_, i) => i !== activeCatalogIndex).map((s) => (
                <div key={s.key} style={{
                  minWidth: "300px",
                  background: "rgba(255, 255, 255, 0.02)",
                  border: "1px solid rgba(255, 255, 255, 0.05)",
                  borderRadius: "24px",
                  padding: "20px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  cursor: "pointer"
                }} onClick={() => setActiveCatalogIndex(metricSeries.indexOf(s))}>
                  <h4 style={{ fontSize: "12px", fontWeight: "900", margin: "0 0 15px 0", color: "rgba(255,255,255,0.6)" }}>{s.label}</h4>
                  <SimpleLineChart points={s.points} width={260} height={100} />
                </div>
              ))}
            </div>
          </div>
        ) : (
         
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: "30px" }}>
            {metricSeries.map((s) => (
              <div key={s.key} style={{
                background: "rgba(255, 255, 255, 0.03)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                borderRadius: "35px",
                padding: "30px",
                backdropFilter: "blur(20px)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center"
              }}>
                <h3 style={{ margin: "0 0 25px 0", fontSize: "16px", fontWeight: "900", color: "#fff", textTransform: "uppercase", letterSpacing: "1px" }}>{s.label}</h3>
                <SimpleLineChart points={s.points} width={380} />
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
import { useMemo, useState } from "react";
//import { useNavigate } from "react-router-dom";
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
import MetricCarousel from "../components/dashboard/MetricCarousel";
import StatusBanner from "../components/dashboard/StatusBanner";
import ChartPanel from "../components/dashboard/ChartPanel";
import { useIncidents } from "../hooks/useIncidents";
import IncidentStatsPanel from "../components/dashboard/IncidentStatsPanel";
import RecentIncidentsFeed from "../components/dashboard/RecentIncidentsFeed";
import IncidentModal from "../components/dashboard/IncidentModal";


const BRAND_ORANGE = "var(--color-top)"; 

export default function Dashboard() {
  const { signup, plan, integrations } = useOnboarding();
 // const navigate = useNavigate();

  const [preset, setPreset] = useState<RangePreset>("week");
  const [customStart, setCustomStart] = useState("2026-01-01");
  const [customEnd, setCustomEnd] = useState("2026-02-20");
  
  const [viewMode, setViewMode] = useState<"focused" | "grid">("focused");
  const [activeCatalogIndex, setActiveCatalogIndex] = useState(0);

  const [selectedIncident, setSelectedIncident] = useState<any | null>(null);

  const range = useMemo(() => {
    if (preset === "custom") return computeRange("custom", { start: customStart, end: customEnd });
    return computeRange(preset);
  }, [preset, customStart, customEnd]);

  const { status, error, series: metricSeries, isMock } = useDashboardData(range);
  const safeActiveIndex =
    metricSeries.length === 0
      ? 0
      : Math.min(activeCatalogIndex, metricSeries.length - 1);
  const connectedCount = useMemo(() => countConnected(integrations), [integrations]);
  const riskScore = useMemo(() => Math.min(100, 35 + connectedCount * 20), [connectedCount]);

  const {
    status: incidentsStatus,
    error: incidentsError,
    incidents,
    stats: incidentStats,
  } = useIncidents();

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
      <main className="flex-grow min-w-0 p-4 md:p-10 lg:p-[60px] overflow-y-auto h-screen">
        
        <DashboardHeader
          companyName={signup?.companyName}
          plan={plan}
          connectedCount={connectedCount}
          riskScore={riskScore}
        />

        <section className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 mb-10">
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

        <StatusBanner status={status} error={error} isMock={isMock} />

        {incidentsStatus === "error" && incidentsError && (
          <div style={{ marginBottom: 18, opacity: 0.9, color: BRAND_ORANGE, fontWeight: 800 }}>
            {incidentsError}
          </div>
        )}

        {viewMode === "focused" ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "30px" }}>
            <ChartPanel
              series={metricSeries}
              activeIndex={safeActiveIndex}
              setActiveIndex={setActiveCatalogIndex}
            />

            <MetricCarousel
              series={metricSeries}
              activeIndex={safeActiveIndex}
              setActiveIndex={setActiveCatalogIndex}
            />
          </div>
        ) : (
         
          <div 
            style={{ 
              display: "grid", 
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
              gap: "30px" 
            }}
          >
            {metricSeries.map((s) => (
              <div 
                key={s.key} 
                style={{
                  background: "rgba(255, 255, 255, 0.03)",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                  borderRadius: "35px",
                  padding: "30px",
                  backdropFilter: "blur(20px)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                }}
              >
                <h3 
                  style={{ 
                    margin: "0 0 25px 0", 
                    fontSize: "16px", 
                    fontWeight: "900", 
                    color: "#fff", 
                    textTransform: "uppercase", 
                    letterSpacing: "1px",
                  }}
                >
                  {s.label}
                </h3>
                <div className="w-full overflow-x-auto flex justify-center">
                  <SimpleLineChart points={s.points} width={380} />
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-[0.9fr_1.1fr] gap-[30px] mt-10">
          <IncidentStatsPanel stats={incidentStats} />
          {/* Updated to handle click */}
          <RecentIncidentsFeed 
            incidents={incidents} 
            onIncidentClick={(incident) => setSelectedIncident(incident)} 
          />
        </div>
        
        <div className="h-24 lg:hidden" />
      </main>

      <IncidentModal
        incident={selectedIncident}
        isOpen={!!selectedIncident}
        onClose={() => setSelectedIncident(null)}
      />

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

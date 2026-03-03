const BRAND_ORANGE = "var(--color-top)";

interface Props {
  fullName: string;
  role: string;
  riskScore: number;      // Calculated from messages_incidents
  flaggedCount: number;   // From Incident_ID (PK) count
  overtimeHours: number;  // Calculated from sent_at timestamps
}

export default function EmployeeCard({ fullName, role, riskScore, flaggedCount, overtimeHours }: Props) {
  return (
    <div style={{
      background: "rgba(255, 255, 255, 0.03)", 
      border: "1px solid rgba(255, 255, 255, 0.08)",
      borderRadius: "35px",
      padding: "30px",
      backdropFilter: "blur(20px)",
      color: "white"
    }}>
      <div style={{ marginBottom: "20px" }}>
        <h2 style={{ margin: 0, fontSize: "24px", fontWeight: "900", color: BRAND_ORANGE }}>
          {fullName.toUpperCase()}
        </h2>
        <p style={{ margin: "4px 0 0 0", fontSize: "11px", fontWeight: "800", opacity: 0.4, letterSpacing: "1.5px" }}>
          {role.toUpperCase()}
        </p>
      </div>

      <div style={{ marginBottom: "25px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
          <span style={{ fontSize: "10px", fontWeight: "900", opacity: 0.6 }}>RISK THREAT LEVEL</span>
          <span style={{ fontSize: "10px", fontWeight: "900", color: BRAND_ORANGE }}>{riskScore}%</span>
        </div>
        <div style={{ width: "100%", height: "4px", background: "rgba(255,255,255,0.1)", borderRadius: "2px" }}>
          <div style={{ width: `${riskScore}%`, height: "100%", background: BRAND_ORANGE, borderRadius: "2px", boxShadow: `0 0 10px ${BRAND_ORANGE}` }} />
        </div>
      </div>

      {/* Backend Metrics Grid */}
      <div style={{ 
        display: "grid", 
        gridTemplateColumns: "1fr 1fr", 
        gap: "20px",
        paddingTop: "20px",
        borderTop: "1px solid rgba(255,255,255,0.05)"
      }}>
        <div>
          <p style={{ fontSize: "10px", fontWeight: "900", opacity: 0.5, margin: "0 0 5px 0" }}>FLAGGED</p>
          <p style={{ fontSize: "22px", fontWeight: "900", margin: 0 }}>{flaggedCount}</p>
        </div>
        <div>
          <p style={{ fontSize: "10px", fontWeight: "900", opacity: 0.5, margin: "0 0 5px 0" }}>OVERTIME</p>
          <p style={{ fontSize: "22px", fontWeight: "900", margin: 0 }}>{overtimeHours}h</p>
        </div>
      </div>
    </div>
  );
}
import type { Incident } from "../../api";

const DEFAULT_RECOMMENDATION =
  "Review this employee's recent communication patterns and consult with HR if the behaviour persists. Ensure any relevant welfare policies are followed.";

interface Props {
  incident: Incident | null;
  isOpen: boolean;
  onClose: () => void;
}

const BRAND_ORANGE = "var(--color-top)";

export default function IncidentModal({ incident, isOpen, onClose }: Props) {
  if (!isOpen || !incident) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(10, 2, 15, 0.85)", 
        backdropFilter: "blur(12px)", 
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: "500px",
          background: "#1a011d",
          border: `1px solid rgba(255, 255, 255, 0.1)`,
          borderRadius: "32px",
          padding: "40px",
          boxShadow: "0 20px 50px rgba(0,0,0,0.5)",
          position: "relative",
          cursor: "default",
        }}
        onClick={(e) => e.stopPropagation()}
      >

        <button
          onClick={onClose}
          style={{
            position: "absolute",
            top: "20px",
            right: "25px",
            background: "transparent",
            border: "none",
            color: "rgba(255,255,255,0.3)",
            fontSize: "24px",
            cursor: "pointer",
          }}
        >
          ×
        </button>

        <div style={{ marginBottom: "30px" }}>
          <div style={{ 
            color: BRAND_ORANGE, 
            fontSize: "11px", 
            fontWeight: 900, 
            letterSpacing: "2px", 
            marginBottom: "8px",
            textTransform: "uppercase" 
          }}>
            Incident Report Analysis
          </div>
          <h2 style={{ 
            margin: 0, 
            fontSize: "24px", 
            fontWeight: 900, 
            color: "#fff",
            textTransform: "capitalize" 
          }}>
            {incident.class_reason}
          </h2>
        </div>

        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "20px",
          padding: "20px",
          background: "rgba(255,255,255,0.03)",
          borderRadius: "20px",
          marginBottom: "30px",
          border: "1px solid rgba(255,255,255,0.05)"
        }}>
          <div>
            <div style={{ fontSize: "10px", opacity: 0.4, fontWeight: 800, textTransform: "uppercase" }}>Date</div>
            <div style={{ fontWeight: 700, fontSize: "14px" }}>
              {incident.created_at ? incident.created_at.slice(0, 10) : new Date().toLocaleDateString()}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "10px", opacity: 0.4, fontWeight: 800, textTransform: "uppercase" }}>Time</div>
            <div style={{ fontWeight: 700, fontSize: "14px" }}>
              {incident.created_at ? incident.created_at.slice(11, 19) : "—"}
            </div>
          </div>
          <div style={{ gridColumn: "span 2" }}>
            <div style={{ fontSize: "10px", opacity: 0.4, fontWeight: 800, textTransform: "uppercase" }}>Channel</div>
            <div style={{ fontWeight: 700, fontSize: "14px", opacity: 0.8 }}>{incident.channel_id || "—"}</div>
          </div>
        </div>

        {/* ADVICE SECTION */}
        <div>
          <div style={{ 
            fontSize: "12px", 
            fontWeight: 900, 
            color: BRAND_ORANGE, 
            marginBottom: "12px",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: BRAND_ORANGE }} />
            SENTINEL ADVICE
          </div>
          <p style={{ 
            fontSize: "15px", 
            lineHeight: "1.6", 
            color: "rgba(255,255,255,0.8)", 
            fontWeight: "500",
            margin: 0
          }}>
            {incident.recommendation || DEFAULT_RECOMMENDATION}
          </p>
        </div>

        <button
          onClick={onClose}
          style={{
            marginTop: "40px",
            width: "100%",
            padding: "16px",
            borderRadius: "16px",
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.1)",
            color: "#fff",
            fontWeight: 800,
            cursor: "pointer",
            transition: "all 0.2s"
          }}
        >
          Dismiss Report
        </button>
      </div>
    </div>
  );
}
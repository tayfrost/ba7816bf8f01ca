import type { Incident } from "../../../api";

const BRAND_ORANGE = "var(--color-top)";

function formatDateTime(iso: string): { date: string; time: string } {
  // Strip timezone and microseconds, keep up to seconds
  const clean = iso.replace(/\+\d{2}:\d{2}$/, "").replace(/Z$/, "").split(".")[0];
  const [date, time] = clean.split("T");
  return { date: date ?? "—", time: time ?? "—" };
}

type Props = {
  incidents: Incident[];
  onIncidentClick: (incident: Incident) => void;
};

export default function EmployeeIncidentTimeline({ incidents, onIncidentClick }: Props) {
  return (
    <div
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "32px",
        padding: "32px",
      }}
    >
      <h3 style={{ marginTop: 0, color: BRAND_ORANGE, letterSpacing: "1px" }}>
        Recent Incident Timeline
      </h3>

      {incidents.length === 0 && (
        <div style={{ padding: "32px", textAlign: "center", opacity: 0.4, fontWeight: 700, fontSize: "14px" }}>
          No incidents recorded
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        {incidents.map((inc) => {
          const { date, time } = formatDateTime(inc.created_at || inc.message_ts || "");
          return (
            <div
              key={inc.message_id}
              onClick={() => onIncidentClick(inc)}
              style={{
                padding: "18px 20px",
                borderRadius: "18px",
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.05)",
                cursor: "pointer",
                transition: "background 0.2s",
              }}
              onMouseOver={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.08)")}
              onMouseOut={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                {/* Timestamp — date + time stacked */}
                <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                  <span style={{ fontSize: "13px", fontWeight: 800, opacity: 0.7 }}>{date}</span>
                  <span style={{ fontSize: "11px", opacity: 0.4 }}>{time}</span>
                </div>
                <span style={{ fontSize: "12px", fontWeight: 900, textTransform: "capitalize", color: BRAND_ORANGE }}>
                  {inc.class_reason}
                </span>
              </div>
              <div style={{ fontWeight: 600, fontSize: "14px", lineHeight: 1.5 }}>
                {inc.raw_message_text?.text || "No message preview available"}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

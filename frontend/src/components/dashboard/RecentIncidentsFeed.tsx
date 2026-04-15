import type { Incident } from "../../api";
import { useEffect } from "react";
import { dashboardDebug } from "../../utils/dashboardDebug";

type Props = {
  incidents: Incident[];
  onIncidentClick: (incident: Incident) => void;
};

export default function RecentIncidentsFeed({ incidents, onIncidentClick }: Props) {
  useEffect(() => {
    dashboardDebug("RecentIncidentsFeed", "render", {
      incidentsCount: incidents.length,
      firstFive: incidents.slice(0, 5).map((incident) => ({
        incident_id: incident.incident_id,
        reason: incident.class_reason,
        created_at: incident.created_at,
        channel_id: incident.channel_id,
        slack_user_id: incident.slack_user_id,
      })),
    });
  }, [incidents]);

  return (
    <div
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "30px",
        padding: "28px",
      }}
    >
      <h3 style={{ margin: "0 0 18px 0", fontWeight: 900, color: "#fff" }}>
        Recent Incidents
      </h3>

      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {incidents.length === 0 && (
          <div style={{ padding: "32px", textAlign: "center", opacity: 0.4, fontWeight: 700, fontSize: "14px" }}>
            No incidents detected
          </div>
        )}
        {incidents.map((incident) => (
          <div
            key={incident.incident_id}
            onClick={() => {
              dashboardDebug("RecentIncidentsFeed", "incident-click", {
                incident_id: incident.incident_id,
                message_id: incident.message_id,
                reason: incident.class_reason,
                created_at: incident.created_at,
              });
              onIncidentClick(incident);
            }} // Handle Click for IncidentModal
            style={{
              padding: "16px",
              borderRadius: "18px",
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.05)",
              cursor: "pointer",
              transition: "background 0.2s"
            }}
            onMouseOver={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.08)")}
            onMouseOut={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "16px",
                marginBottom: "8px",
              }}
            >
              <span style={{ fontSize: "12px", opacity: 0.5 }}>
                {incident.created_at ? incident.created_at.slice(0, 10) : ""}
              </span>
              <span
                style={{
                  fontSize: "12px",
                  fontWeight: 800,
                  textTransform: "capitalize",
                  color: "var(--color-top)",
                }}
              >
                {incident.class_reason}
              </span>
            </div>

            <div style={{ fontWeight: 700, marginBottom: "8px" }}>
              {incident.raw_message_text?.text || "No message preview available"}
            </div>

            <div style={{ fontSize: "12px", opacity: 0.5 }}>
              Channel: {incident.channel_id} • User: {incident.slack_user_id}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
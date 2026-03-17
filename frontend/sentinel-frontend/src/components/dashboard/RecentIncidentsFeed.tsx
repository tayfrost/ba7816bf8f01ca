import type { Incident } from "../../api";

type Props = {
  incidents: Incident[];
};

export default function RecentIncidentsFeed({ incidents }: Props) {
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
        {incidents.map((incident) => (
          <div
            key={incident.incident_id}
            style={{
              padding: "16px",
              borderRadius: "18px",
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.05)",
            }}
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
                #{incident.incident_id}
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
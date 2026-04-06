const BRAND_ORANGE = "var(--color-top)";

type Props = {
  incidents: string[];
};

export default function EmployeeIncidentTimeline({ incidents }: Props) {
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

      <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        {incidents.map((item, idx) => (
          <div
            key={idx}
            style={{
              padding: "18px 20px",
              borderRadius: "18px",
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.05)",
            }}
          >
            <div style={{ fontSize: "12px", opacity: 0.45, marginBottom: "6px" }}>
              Incident #{idx + 1}
            </div>
            <div style={{ fontWeight: 700 }}>{item}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
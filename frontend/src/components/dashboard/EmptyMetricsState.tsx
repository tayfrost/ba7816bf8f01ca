export default function EmptyMetricsState() {
  return (
    <div
      style={{
        background: "rgba(255, 255, 255, 0.03)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "35px",
        padding: "60px",
        textAlign: "center",
        opacity: 0.8,
      }}
    >
      <h3 style={{ margin: 0, fontSize: "22px", fontWeight: 900 }}>
        No metrics available
      </h3>
      <p style={{ marginTop: "12px", opacity: 0.6 }}>
        Connect a monitored workspace and allow the system to ingest incidents.
      </p>
    </div>
  );
}
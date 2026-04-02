export default function NotificationsPreferences() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {[
        "High risk employee detected",
        "Burnout score exceeded",
        "Critical message flagged",
        "Weekly analytics report",
      ].map((item) => (
        <label
          key={item}
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            background: "rgba(255,255,255,0.03)",
            padding: "14px 18px",
            borderRadius: "14px",
            border: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          <span style={{ fontSize: "13px", fontWeight: 700 }}>{item}</span>

          <input type="checkbox" defaultChecked />
        </label>
      ))}
    </div>
  );
}
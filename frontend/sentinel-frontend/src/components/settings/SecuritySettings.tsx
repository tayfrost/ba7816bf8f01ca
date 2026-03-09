import Button from "../Button";

export default function SecuritySettings() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <p style={{ margin: 0, fontWeight: 800 }}>Two-Factor Authentication</p>
          <p style={{ margin: 0, fontSize: "12px", opacity: 0.5 }}>
            Add an extra security layer to your admin account.
          </p>
        </div>

        <Button variant="secondary" className="!text-white !bg-white/20 hover:!bg-white/30">
          Enable
        </Button>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <p style={{ margin: 0, fontWeight: 800 }}>Session Timeout</p>
          <p style={{ margin: 0, fontSize: "12px", opacity: 0.5 }}>
            Automatically log out inactive admin sessions.
          </p>
        </div>

        <select
          style={{
            background: "rgba(255,255,255,0.1)",
            border: "1px solid rgba(255,255,255,0.2)",
            color: "white",
            padding: "8px 12px",
            borderRadius: "10px",
          }}
        >
          <option>15 minutes</option>
          <option>30 minutes</option>
          <option>1 hour</option>
        </select>
      </div>
    </div>
  );
}
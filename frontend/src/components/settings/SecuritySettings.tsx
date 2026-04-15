import { useState } from "react";
import Button from "../Button";

export const SESSION_DAYS_KEY = "sentinel_session_days";
export const SESSION_DAYS_DEFAULT = 1;

const SESSION_OPTIONS = [
  { label: "1 Day", value: 1 },
  { label: "7 Days", value: 7 },
  { label: "30 Days", value: 30 },
];

function loadSessionDays(): number {
  try {
    const raw = localStorage.getItem(SESSION_DAYS_KEY);
    const parsed = raw ? parseInt(raw, 10) : NaN;
    return SESSION_OPTIONS.some((o) => o.value === parsed) ? parsed : SESSION_DAYS_DEFAULT;
  } catch {
    return SESSION_DAYS_DEFAULT;
  }
}

export default function SecuritySettings() {
  const [sessionDays, setSessionDays] = useState<number>(loadSessionDays);

  function handleSessionChange(days: number) {
    setSessionDays(days);
    try {
      localStorage.setItem(SESSION_DAYS_KEY, String(days));
    } catch { void 0; }
  }

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
          <p style={{ margin: 0, fontWeight: 800 }}>Session Duration</p>
          <p style={{ margin: 0, fontSize: "12px", opacity: 0.5 }}>
            How long you stay logged in. Takes effect on next login.
          </p>
        </div>

        <select
          value={sessionDays}
          onChange={(e) => handleSessionChange(Number(e.target.value))}
          style={{
            background: "rgba(255,255,255,0.1)",
            border: "1px solid rgba(255,255,255,0.2)",
            color: "white",
            padding: "8px 12px",
            borderRadius: "10px",
            cursor: "pointer",
          }}
        >
          {SESSION_OPTIONS.map((o) => (
            <option key={o.value} value={o.value} style={{ background: "#1a011d" }}>
              {o.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
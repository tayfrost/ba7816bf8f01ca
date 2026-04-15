import type { Employee } from "../../../types/employees";

const BRAND_ORANGE = "var(--color-top)";

type Props = {
  employee: Employee;
};

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{ padding: "16px", borderRadius: "18px", background: "rgba(255,255,255,0.04)" }}>
      <div style={{ opacity: 0.5, fontSize: "12px", marginBottom: "6px" }}>{label}</div>
      <div style={{ fontSize: "28px", fontWeight: 900 }}>{value}</div>
    </div>
  );
}

function DateTimeCard({ label, iso }: { label: string; iso: string }) {
  const clean = iso.replace(/\+\d{2}:\d{2}$/, "").replace(/Z$/, "").split(".")[0];
  const [date, time] = clean.split("T");
  return (
    <div style={{ padding: "16px", borderRadius: "18px", background: "rgba(255,255,255,0.04)" }}>
      <div style={{ opacity: 0.5, fontSize: "12px", marginBottom: "8px" }}>{label}</div>
      <div style={{ fontSize: "18px", fontWeight: 900 }}>{date || "—"}</div>
      <div style={{ fontSize: "13px", fontWeight: 700, opacity: 0.5, marginTop: "4px" }}>{time || ""}</div>
    </div>
  );
}

export default function EmployeeWorkloadSummary({ employee }: Props) {
  return (
    <div
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "32px",
        padding: "32px",
        display: "flex",
        flexDirection: "column",
        gap: "18px",
      }}
    >
      <h3 style={{ margin: 0, color: BRAND_ORANGE, letterSpacing: "1px" }}>
        Workload Summary
      </h3>

      <StatCard label="Flagged messages" value={employee.flaggedCount} />
      <StatCard label="Overtime hours" value={`${employee.overtimeHours}h`} />
      {employee.lastActive
        ? <DateTimeCard label="Last active" iso={employee.lastActive} />
        : <StatCard label="Last active" value="No activity" />
      }
    </div>
  );
}
import EmployeeSources from "./employees/EmployeeSources";
import EmployeeStatsRow from "./employees/EmployeeStatsRow";
import EmployeeRiskMiniChart from "./employees/EmployeeRiskMiniChart";

type Point = {
  date: string;
  value: number;
};

type Props = {
  fullName: string;
  role: string;
  email: string;
  team: string;
  riskScore: number;
  flaggedCount: number;
  overtimeHours: number;
  lastActive: string;
  sources: ("slack" | "gmail" | "outlook")[];
  trend: Point[];
};

export default function EmployeeCard({
  fullName,
  role,
  email,
  team,
  riskScore,
  flaggedCount,
  overtimeHours,
  lastActive,
  sources,
  trend,
}: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <div>
        <h3
          style={{
            margin: 0,
            fontSize: "22px",
            fontWeight: 900,
            letterSpacing: "-0.5px",
            color: "#fff",
          }}
        >
          {fullName}
        </h3>

        <p
          style={{
            margin: "8px 0 0 0",
            fontSize: "13px",
            fontWeight: 700,
            color: "rgba(255,255,255,0.58)",
          }}
        >
          {role}
        </p>

        <p
          style={{
            margin: "6px 0 0 0",
            fontSize: "12px",
            fontWeight: 600,
            color: "rgba(255,255,255,0.38)",
          }}
        >
          {email}
        </p>
      </div>

      <EmployeeSources sources={sources} />

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "10px",
          padding: "14px 16px",
          borderRadius: "18px",
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <span
          style={{
            fontSize: "11px",
            fontWeight: 900,
            letterSpacing: "1px",
            textTransform: "uppercase",
            opacity: 0.45,
          }}
        >
          Current risk
        </span>

        <span
          style={{
            fontSize: "24px",
            fontWeight: 900,
            color: "#fff",
          }}
        >
          {riskScore}%
        </span>
      </div>

      <EmployeeStatsRow
        flaggedCount={flaggedCount}
        overtimeHours={overtimeHours}
        team={team}
        lastActive={lastActive}
      />

      <EmployeeRiskMiniChart points={trend} />
    </div>
  );
}
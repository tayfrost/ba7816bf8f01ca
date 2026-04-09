import type { EmployeeSource, RiskLevel } from "../../types/employees";
import type { EmployeeSort } from "../../hooks/useEmployeesData";

type Props = {
  riskFilter: RiskLevel | "all";
  setRiskFilter: (v: RiskLevel | "all") => void;

  sourceFilter: EmployeeSource | "all";
  setSourceFilter: (v: EmployeeSource | "all") => void;

  sortBy: EmployeeSort;
  setSortBy: (v: EmployeeSort) => void;
};

const STYLE = {
  background: "rgba(0,0,0,0.45)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: "20px",
  padding: "10px 16px",
  color: "white",
  fontWeight: 700,
  fontSize: "12px",
};

export default function EmployeesFilters({
  riskFilter,
  setRiskFilter,
  sourceFilter,
  setSourceFilter,
  sortBy,
  setSortBy,
}: Props) {
  return (
    <div
      style={{
        display: "flex",
        gap: "15px",
        flexWrap: "wrap",
        marginBottom: "30px",
      }}
    >
      {/* Risk filter */}
      <select
        value={riskFilter}
        onChange={(e) => setRiskFilter(e.target.value as RiskLevel | "all")}
        style={STYLE}
      >
        <option value="all">All risk</option>
        <option value="low">Low risk</option>
        <option value="medium">Medium risk</option>
        <option value="high">High risk</option>
        <option value="critical">Critical</option>
      </select>

      {/* Source filter */}
      <select
        value={sourceFilter}
        onChange={(e) => setSourceFilter(e.target.value as EmployeeSource | "all")}
        style={STYLE}
      >
        <option value="all">All sources</option>
        <option value="slack">Slack</option>
        <option value="gmail">Gmail</option>
      </select>

      {/* Sort */}
      <select
        value={sortBy}
        onChange={(e) => setSortBy(e.target.value as EmployeeSort)}
        style={STYLE}
      >
        <option value="risk-desc">Risk ↓</option>
        <option value="risk-asc">Risk ↑</option>
        <option value="flagged-desc">Flagged ↓</option>
        <option value="name-asc">Name A-Z</option>
      </select>
    </div>
  );
}
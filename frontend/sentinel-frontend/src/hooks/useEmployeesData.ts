import { useMemo, useState } from "react";
import { MOCK_EMPLOYEES, sortEmployeesByRisk, type Employee, type EmployeeSource, type RiskLevel, getRiskLevel } from "../state/employeesMock";

export type EmployeeSort = "risk-desc" | "risk-asc" | "name-asc" | "flagged-desc";

function matchesRiskLevel(employee: Employee, level: RiskLevel | "all") {
  if (level === "all") return true;
  return getRiskLevel(employee.riskScore) === level;
}

function matchesSource(employee: Employee, source: EmployeeSource | "all") {
  if (source === "all") return true;
  return employee.source.includes(source);
}

function sortEmployees(employees: Employee[], sortBy: EmployeeSort) {
  const copy = [...employees];

  if (sortBy === "risk-desc") {
    return copy.sort((a, b) => b.riskScore - a.riskScore);
  }

  if (sortBy === "risk-asc") {
    return copy.sort((a, b) => a.riskScore - b.riskScore);
  }

  if (sortBy === "name-asc") {
    return copy.sort((a, b) => a.fullName.localeCompare(b.fullName));
  }

  return copy.sort((a, b) => b.flaggedCount - a.flaggedCount);
}

export function useEmployeesData() {
  const [searchTerm, setSearchTerm] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskLevel | "all">("all");
  const [sourceFilter, setSourceFilter] = useState<EmployeeSource | "all">("all");
  const [sortBy, setSortBy] = useState<EmployeeSort>("risk-desc");

  const employees = useMemo(() => {
    const normalized = searchTerm.trim().toLowerCase();

    const filtered = MOCK_EMPLOYEES.filter((employee) => {
      const matchesSearch =
        normalized.length === 0 ||
        employee.fullName.toLowerCase().includes(normalized) ||
        employee.role.toLowerCase().includes(normalized) ||
        employee.team.toLowerCase().includes(normalized) ||
        employee.email.toLowerCase().includes(normalized);

      return (
        matchesSearch &&
        matchesRiskLevel(employee, riskFilter) &&
        matchesSource(employee, sourceFilter)
      );
    });

    return sortEmployees(filtered, sortBy);
  }, [searchTerm, riskFilter, sourceFilter, sortBy]);

  const stats = useMemo(() => {
    const total = MOCK_EMPLOYEES.length;
    const critical = MOCK_EMPLOYEES.filter((e) => getRiskLevel(e.riskScore) === "critical").length;
    const high = MOCK_EMPLOYEES.filter((e) => getRiskLevel(e.riskScore) === "high").length;
    const watchlist = MOCK_EMPLOYEES.filter((e) => e.status === "watchlist" || e.status === "critical").length;

    const flagged = MOCK_EMPLOYEES.reduce((sum, e) => sum + e.flaggedCount, 0);
    
    const avgRisk =
      total === 0
        ? 0
        : Math.round(
          MOCK_EMPLOYEES.reduce((sum, e) => sum + e.riskScore, 0) / total
        );

    return { total, critical, high, watchlist, flagged, avgRisk };
  }, []);

  return {
    employees,
    stats,
    searchTerm,
    setSearchTerm,
    riskFilter,
    setRiskFilter,
    sourceFilter,
    setSourceFilter,
    sortBy,
    setSortBy,
  };
}
import { useEffect, useMemo, useState } from "react";
import { getEmployees } from "../api";
import type { Employee, EmployeeSource, RiskLevel } from "../types/employees";
import { getRiskLevel } from "../types/employees";

export type EmployeeSort = "risk-desc" | "risk-asc" | "name-asc" | "flagged-desc";
type Status = "idle" | "loading" | "success" | "error";

function matchesRiskLevel(employee: Employee, level: RiskLevel | "all") {
  if (level === "all") return true;
  return getRiskLevel(employee.riskScore) === level;
}

function matchesSource(employee: Employee, source: EmployeeSource | "all") {
  if (source === "all") return true;
  return employee.source.includes(source);
}

function getSurname(fullName: string): string {
  const parts = fullName.trim().split(/\s+/);
  return parts[parts.length - 1].toLowerCase();
}

function sortEmployees(employees: Employee[], sortBy: EmployeeSort) {
  const copy = [...employees];
  if (sortBy === "risk-desc") return copy.sort((a, b) => b.riskScore - a.riskScore);
  if (sortBy === "risk-asc") return copy.sort((a, b) => a.riskScore - b.riskScore);
  if (sortBy === "name-asc") return copy.sort((a, b) => {
    const sA = getSurname(a.fullName);
    const sB = getSurname(b.fullName);
    return sA !== sB ? sA.localeCompare(sB) : a.fullName.localeCompare(b.fullName);
  });
  return copy.sort((a, b) => b.flaggedCount - a.flaggedCount);
}

export function useEmployeesData() {
  const [rawEmployees, setRawEmployees] = useState<Employee[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskLevel | "all">("all");
  const [sourceFilter, setSourceFilter] = useState<EmployeeSource | "all">("all");
  const [sortBy, setSortBy] = useState<EmployeeSort>("risk-desc");

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setStatus("loading");
      setError(null);

      try {
        const res = await getEmployees();
        if (cancelled) return;
        setRawEmployees(res.employees);
        setStatus("success");
      } catch (err) {
        if (cancelled) return;
        console.error(err);
        setRawEmployees([]);
        setStatus("error");
        setError("Failed to load monitored employees.");
      }
    }

    run();
    return () => { cancelled = true; };
  }, []);

  const employees = useMemo(() => {
    const normalized = searchTerm.trim().toLowerCase();

    const filtered = rawEmployees.filter((employee) => {
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
  }, [rawEmployees, searchTerm, riskFilter, sourceFilter, sortBy]);

  const stats = useMemo(() => {
    const total = rawEmployees.length;
    const critical = rawEmployees.filter((e) => getRiskLevel(e.riskScore) === "critical").length;
    const high = rawEmployees.filter((e) => getRiskLevel(e.riskScore) === "high").length;
    const watchlist = rawEmployees.filter(
      (e) => e.status === "watchlist" || e.status === "critical"
    ).length;
    const flagged = rawEmployees.reduce((sum, e) => sum + e.flaggedCount, 0);
    const avgRisk =
      total === 0
        ? 0
        : Math.round(rawEmployees.reduce((sum, e) => sum + e.riskScore, 0) / total);

    return { total, critical, high, watchlist, flagged, avgRisk };
  }, [rawEmployees]);

  return {
    employees,
    stats,
    status,
    error,
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

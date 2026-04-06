import { useEffect, useMemo, useState } from "react";
import { getSlackUsers } from "../api";
import type { Employee, EmployeeSource, RiskLevel } from "../types/employees";
import { getRiskLevel } from "../state/employeesMock";

export type EmployeeSort = "risk-desc" | "risk-asc" | "name-asc" | "flagged-desc";
type Status = "idle" | "loading" | "success" | "error";

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function seededRandom(seed: number) {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

function makeTrend(seedOffset: number, start = "2026-02-01", end = "2026-03-09") {
  const out: { date: string; value: number }[] = [];
  const startDate = new Date(`${start}T00:00:00`);
  const endDate = new Date(`${end}T00:00:00`);
  const current = new Date(startDate);

  while (current <= endDate) {
    const yyyy = current.getFullYear();
    const mm = String(current.getMonth() + 1).padStart(2, "0");
    const dd = String(current.getDate()).padStart(2, "0");
    const date = `${yyyy}-${mm}-${dd}`;

    const seed = Number(date.replaceAll("-", "")) + seedOffset;
    const r = seededRandom(seed);

    out.push({
      date,
      value: clamp(Math.round(25 + r * 70), 0, 100),
    });

    current.setDate(current.getDate() + 1);
  }

  return out;
}

function deriveStatus(score: number): "active" | "watchlist" | "critical" {
  if (score >= 85) return "critical";
  if (score >= 45) return "watchlist";
  return "active";
}

function mapSlackUserToEmployee(user: {
  id: number;
  team_id: string;
  slack_user_id: string;
  name: string;
  surname: string;
  created_at: string;
  status: string;
}): Employee {
  const seed = user.id * 97;

  const riskScore = clamp(Math.round(20 + seededRandom(seed) * 75), 0, 100);
  const flaggedCount = clamp(Math.round(seededRandom(seed + 10) * 18), 0, 30);
  const overtimeHours = clamp(Math.round(2 + seededRandom(seed + 20) * 20), 0, 24);

  return {
    id: String(user.id),
    fullName: `${user.name} ${user.surname}`.trim(),
    role: "Slack Workforce Member",
    team: user.team_id || "Slack Team",
    email: `${user.name.toLowerCase()}.${user.surname.toLowerCase()}@slack.local`,
    source: ["slack"],
    riskScore,
    flaggedCount,
    overtimeHours,
    lastActive: new Date(user.created_at).toLocaleDateString(),
    status: deriveStatus(riskScore),
    trend: makeTrend(seed),
  };
}

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
        const users = await getSlackUsers();
        if (cancelled) return;

        const mapped = users.map(mapSlackUserToEmployee);
        setRawEmployees(mapped);
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

    return () => {
      cancelled = true;
    };
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
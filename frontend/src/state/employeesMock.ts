import { enumerateDays } from "./timeRange";

export type EmployeeSource = "slack" | "gmail" | "outlook";
export type RiskLevel = "low" | "medium" | "high" | "critical";

export type Employee = {
  id: string;
  fullName: string;
  role: string;
  team: string;
  email: string;
  source: EmployeeSource[];
  riskScore: number;
  flaggedCount: number;
  overtimeHours: number;
  lastActive: string;
  status: "active" | "watchlist" | "critical";
  trend: { date: string; value: number }[];
};

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function seededRandom(seed: number) {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

function makeTrend(seedOffset: number, start = "2026-02-01", end = "2026-03-09") {
  const days = enumerateDays(start, end);

  return days.map((d, i) => {
    const seed = Number(d.replaceAll("-", "")) + seedOffset + i;
    const r = seededRandom(seed);
    return {
      date: d,
      value: clamp(Math.round(25 + r * 70), 0, 100),
    };
  });
}

function deriveRiskLevel(score: number): RiskLevel {
  if (score >= 85) return "critical";
  if (score >= 65) return "high";
  if (score >= 35) return "medium";
  return "low";
}

export function getRiskLevel(score: number): RiskLevel {
  return deriveRiskLevel(score);
}

export const MOCK_EMPLOYEES: Employee[] = [
  {
    id: "u1",
    fullName: "Sarah Jenkins",
    role: "Senior Engineer",
    team: "Platform",
    email: "sarah.jenkins@sentinel.test",
    source: ["slack", "gmail"],
    riskScore: 82,
    flaggedCount: 14,
    overtimeHours: 12,
    lastActive: "Today, 09:42",
    status: "watchlist",
    trend: makeTrend(101),
  },
  {
    id: "u2",
    fullName: "Marcus Chen",
    role: "Product Manager",
    team: "Product",
    email: "marcus.chen@sentinel.test",
    source: ["gmail", "outlook"],
    riskScore: 15,
    flaggedCount: 2,
    overtimeHours: 4,
    lastActive: "Today, 11:15",
    status: "active",
    trend: makeTrend(202),
  },
  {
    id: "u3",
    fullName: "Elena Rodriguez",
    role: "UX Designer",
    team: "Design",
    email: "elena.rodriguez@sentinel.test",
    source: ["slack"],
    riskScore: 45,
    flaggedCount: 7,
    overtimeHours: 9,
    lastActive: "Yesterday, 18:26",
    status: "watchlist",
    trend: makeTrend(303),
  },
  {
    id: "u4",
    fullName: "David Kim",
    role: "DevOps Engineer",
    team: "Infrastructure",
    email: "david.kim@sentinel.test",
    source: ["slack", "gmail", "outlook"],
    riskScore: 91,
    flaggedCount: 28,
    overtimeHours: 22,
    lastActive: "Today, 07:58",
    status: "critical",
    trend: makeTrend(404),
  },
  {
    id: "u5",
    fullName: "Priya Nair",
    role: "Data Analyst",
    team: "Insights",
    email: "priya.nair@sentinel.test",
    source: ["gmail"],
    riskScore: 58,
    flaggedCount: 10,
    overtimeHours: 11,
    lastActive: "Today, 10:04",
    status: "watchlist",
    trend: makeTrend(505),
  },
  {
    id: "u6",
    fullName: "Tom Becker",
    role: "Customer Success Lead",
    team: "Operations",
    email: "tom.becker@sentinel.test",
    source: ["outlook"],
    riskScore: 29,
    flaggedCount: 3,
    overtimeHours: 5,
    lastActive: "Yesterday, 16:40",
    status: "active",
    trend: makeTrend(606),
  },
];

export function sortEmployeesByRisk(employees: Employee[]) {
  return [...employees].sort((a, b) => b.riskScore - a.riskScore);
}
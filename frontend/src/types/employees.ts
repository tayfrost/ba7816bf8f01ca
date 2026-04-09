export type EmployeeSource = "slack" | "gmail";
export type RiskLevel = "low" | "medium" | "high" | "critical";

export function getRiskLevel(score: number): RiskLevel {
  if (score >= 85) return "critical";
  if (score >= 65) return "high";
  if (score >= 35) return "medium";
  return "low";
}

export type EmployeeStatus = "active" | "watchlist" | "critical";

export type EmployeeTrendPoint = {
  date: string;
  value: number;
};

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
  status: EmployeeStatus;
  trend: EmployeeTrendPoint[];
};

export type EmployeesResponse = {
  employees: Employee[];
};
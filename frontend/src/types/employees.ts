export type EmployeeSource = "slack" | "gmail";
export type RiskLevel = "low" | "medium" | "high" | "critical";

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
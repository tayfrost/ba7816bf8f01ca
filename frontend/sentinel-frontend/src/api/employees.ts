import { apiFetch } from "./client";
import type { EmployeesResponse } from "../types/employees";

export async function getEmployees(): Promise<EmployeesResponse> {
  return apiFetch<EmployeesResponse>("/employees");
}
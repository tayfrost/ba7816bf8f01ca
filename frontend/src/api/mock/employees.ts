import { MOCK_EMPLOYEES } from "../../state/employeesMock";
import type { EmployeesResponse } from "../../types/employees";

export async function getEmployees(): Promise<EmployeesResponse> {
  return {
    employees: MOCK_EMPLOYEES,
  };
}
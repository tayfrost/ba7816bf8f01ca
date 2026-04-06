import { apiFetch } from "./client";

export type CompanyResponse = {
  company_id: number;
  plan_id: number;
  company_name: string;
  created_at: string;
  deleted_at: string | null;
  stripe_customer_id: string | null;
};

export async function getMyCompany(): Promise<CompanyResponse> {
  return apiFetch<CompanyResponse>("/companies/me");
}

export async function updateMyCompany(payload: {
  company_name: string;
}): Promise<CompanyResponse> {
  return apiFetch<CompanyResponse>("/companies/me", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteMyCompany(): Promise<{ detail: string }> {
  return apiFetch<{ detail: string }>("/companies/me", {
    method: "DELETE",
  });
}
import { apiFetch } from "./client";

export type RegisterPayload = {
  email: string;
  password: string;
  name: string;
  surname: string;
  display_name: string;
  company_name: string;
  plan_id: number;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
};

export type MeResponse = {
  user_id: number;
  name: string;
  surname: string;
  email: string;
  company_id: number;
  role: string;
  status: string;
};

export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getMe(): Promise<MeResponse> {
  return apiFetch<MeResponse>("/auth/me");
}
import { apiFetch } from "./client";

export type Provider = "slack" | "gmail";

export type IntegrationStatus = {
  provider: Provider;
  connected: boolean;
  connectedAt?: string;
};

export async function getIntegrations(): Promise<IntegrationStatus[]> {
  return apiFetch<IntegrationStatus[]>("/integrations");
}

export async function startIntegration(provider: Provider): Promise<{ url: string }> {
  return apiFetch<{ url: string }>(`/integrations/${provider}/start`, { method: "POST" });
}

export async function disconnectIntegration(provider: Provider): Promise<void> {
  return apiFetch<void>(`/integrations/${provider}`, { method: "DELETE" });
}

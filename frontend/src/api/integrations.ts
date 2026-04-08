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

/** Any authenticated user can connect their own Gmail mailbox (no admin role required). */
export async function startPersonalGmail(): Promise<{ url: string }> {
  return apiFetch<{ url: string }>("/integrations/gmail/personal/start", { method: "POST" });
}

/**
 * Team member self-registration flow. Identical auth requirements to startPersonalGmail
 * but the OAuth callback returns to /register-gmail instead of /connect-accounts.
 */
export async function startMemberGmail(): Promise<{ url: string }> {
  return apiFetch<{ url: string }>("/integrations/gmail/member/start", { method: "POST" });
}

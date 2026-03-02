import type { IntegrationStatus, Provider } from "../integrations";

const DEFAULT: IntegrationStatus[] = [
  { provider: "slack", connected: false },
  { provider: "gmail", connected: false },
  { provider: "outlook", connected: false },
];

export async function getIntegrations(): Promise<IntegrationStatus[]> {
  return DEFAULT;
}

export async function startIntegration(provider: Provider): Promise<{ url: string }> {
  return { url: `/oauth/${provider}/start` };
}

export async function disconnectIntegration(_provider: Provider): Promise<void> {
  return;
}
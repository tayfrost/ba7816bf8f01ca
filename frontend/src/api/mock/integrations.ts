import type { IntegrationStatus, Provider } from "../integrations";

let state: IntegrationStatus[] = [
  { provider: "slack", connected: false, connectedAt: null as unknown as string | undefined },
  { provider: "gmail", connected: false, connectedAt: null as unknown as string | undefined },
  { provider: "outlook", connected: false, connectedAt: null as unknown as string | undefined },
];

export async function getIntegrations(): Promise<IntegrationStatus[]> {
  return state;
}

export async function startIntegration(provider: Provider): Promise<{ url: string }> {
  state = state.map((i) =>
    i.provider === provider
      ? { ...i, connected: true, connectedAt: new Date().toISOString() }
      : i
  );

  return { url: `/mock-oauth/${provider}` };
}

export async function disconnectIntegration(provider: Provider): Promise<void> {
  state = state.map((i) =>
    i.provider === provider
      ? { ...i, connected: false, connectedAt: undefined }
      : i
  );
}
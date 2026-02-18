import { Integration } from "./onboarding";

export function hasAnyIntegrationConnected(integrations: Integration[]): boolean {
  return integrations.some(i => i.connected);
}

export function getConnectedProviders(integrations: Integration[]) {
  return integrations
    .filter(i => i.connected)
    .map(i => i.provider);
}

export function countConnected(integrations: Integration[]): number {
  return integrations.filter(i => i.connected).length;
}

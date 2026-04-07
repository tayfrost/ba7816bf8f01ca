import { useOnboarding } from "../../../state/onboarding";
import IntegrationCard from "./IntegrationCard";
import { startIntegration, disconnectIntegration } from "../../../api";

export default function IntegrationsPanel() {
  const { integrations, setIntegrationConnected } = useOnboarding();

  async function connect(provider: "slack" | "gmail") {
    try {
      const res = await startIntegration(provider);

      if (res?.url) {
        window.open(res.url, "_blank");
      }

      setIntegrationConnected(provider, true);
    } catch {
      alert("Failed to connect integration");
    }
  }

  async function disconnect(provider: "slack" | "gmail") {
    try {
      await disconnectIntegration(provider);
      setIntegrationConnected(provider, false);
    } catch {
      alert("Failed to disconnect integration");
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      {integrations.map((i) => (
        <IntegrationCard
          key={i.provider}
          provider={i.provider}
          connected={i.connected}
          connectedAt={i.connectedAt}
          onConnect={() => connect(i.provider)}
          onDisconnect={() => disconnect(i.provider)}
        />
      ))}
    </div>
  );
}

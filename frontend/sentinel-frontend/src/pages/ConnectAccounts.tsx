import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/Button";
import { useOnboarding } from "../state/onboarding";

type Provider = "slack" | "gmail" | "outlook";

function providerTitle(p: Provider) {
  if (p === "slack") return "Slack";
  if (p === "gmail") return "Gmail";
  return "Outlook";
}

function providerDesc(p: Provider) {
  if (p === "slack") return "Connect a workspace to ingest messages via approved channels.";
  if (p === "gmail") return "Connect mailbox metadata (consent-based) for behavioural signals.";
  return "Connect Outlook to ingest organisational communication signals.";
}

export default function ConnectAccounts() {
  const nav = useNavigate();
  const { accountsConnected, setAccountsConnected } = useOnboarding();

  const providers = useMemo<Provider[]>(() => ["slack", "gmail", "outlook"], []);

  const connectMock = (provider: Provider) => {
    // For now we mock a successful connect to unblock demo.
    // Backend can later replace this with OAuth start endpoint.
    console.log("connect provider:", provider);
    setAccountsConnected(true);
  };

  const continueToDashboard = () => {
    nav("/usage", { replace: true });
  };

  return (
    <div style={{ maxWidth: 920, margin: "0 auto", padding: 24 }}>
      <h1 style={{ fontSize: 28, marginBottom: 8 }}>Connect your work accounts</h1>
      <p style={{ opacity: 0.85, marginBottom: 18 }}>
        Add Slack/Gmail/Outlook so SentinelAI can monitor early burnout signals using consent-based,
        company-approved data sources.
      </p>

      <div style={{ display: "grid", gap: 14 }}>
        {providers.map((p) => (
          <div
            key={p}
            style={{
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 14,
              padding: 16,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>{providerTitle(p)}</div>
              <div style={{ opacity: 0.8, marginTop: 4 }}>{providerDesc(p)}</div>
            </div>

            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span style={{ opacity: 0.75 }}>
                {accountsConnected ? "Connected" : "Not connected"}
              </span>
              <Button onClick={() => connectMock(p)}>
                {accountsConnected ? "Reconnect" : "Connect"}
              </Button>
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 18, display: "flex", gap: 10 }}>
        <Button onClick={continueToDashboard} variant="secondary">
          Skip for now
        </Button>
        <Button onClick={continueToDashboard} disabled={!accountsConnected}>
          Continue
        </Button>
      </div>
    </div>
  );
}

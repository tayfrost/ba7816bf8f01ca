import Stepper from "../components/Stepper";
import { useMemo } from "react";
import { useOnboarding } from "../state/onboarding";
import { countConnected, getConnectedProviders } from "../state/integrationRules";

type AlertSeverity = "low" | "medium" | "high";

type MockAlert = {
  id: string;
  provider: string;
  severity: AlertSeverity;
  message: string;
  createdAt: string;
};

function generateMockRiskScore(connectedCount: number) {
  if (connectedCount === 0) return 0;
  return Math.min(100, 35 + connectedCount * 20);
}

function generateMockAlerts(providers: string[]): MockAlert[] {
  return providers.map((p, index) => ({
    id: `${p}-${index}`,
    provider: p,
    severity: index % 2 === 0 ? "medium" : "low",
    message: `Elevated stress indicators detected in ${p} activity.`,
    createdAt: new Date(Date.now() - index * 86400000).toISOString(),
  }));
}

export default function Usage() {
  const { signup, plan, integrations, reset } = useOnboarding();

  const connectedCount = useMemo(
    () => countConnected(integrations),
    [integrations]
  );

  const connectedProviders = useMemo(
    () => getConnectedProviders(integrations),
    [integrations]
  );

  const riskScore = useMemo(
    () => generateMockRiskScore(connectedCount),
    [connectedCount]
  );

  const alerts = useMemo(
    () => generateMockAlerts(connectedProviders),
    [connectedProviders]
  );

  return (
    <div>
      <Stepper currentPath="/usage" />

      <div style={{ padding: 24 }}>
        <h1>Usage overview</h1>

        <section style={{ marginTop: 24 }}>
          <h2>Organisation Summary</h2>
          <p><strong>Company:</strong> {signup?.companyName}</p>
          <p><strong>Plan:</strong> {plan}</p>
          <p><strong>Connected Providers:</strong> {connectedCount}</p>
        </section>

        <section style={{ marginTop: 32 }}>
          <h2>Risk Overview (Mock)</h2>
          <p><strong>Current Risk Score:</strong> {riskScore}%</p>
          <p>
            Risk score is derived from connected data sources and behavioural signals.
          </p>
        </section>

        <section style={{ marginTop: 32 }}>
          <h2>Connected Integrations</h2>
          {connectedProviders.length === 0 ? (
            <p>No integrations connected yet.</p>
          ) : (
            <ul>
              {connectedProviders.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          )}
        </section>

        <section style={{ marginTop: 32 }}>
          <h2>Recent Alerts (Mock)</h2>
          {alerts.length === 0 ? (
            <p>No alerts generated yet.</p>
          ) : (
            <ul>
              {alerts.map((alert) => (
                <li key={alert.id} style={{ marginBottom: 12 }}>
                  <strong>{alert.provider}</strong> — {alert.severity.toUpperCase()} <br />
                  {alert.message} <br />
                  <small>{new Date(alert.createdAt).toLocaleString()}</small>
                </li>
              ))}
            </ul>
          )}
        </section>

        <div style={{ marginTop: 40 }}>
          <button onClick={reset}>
            Reset demo state
          </button>
        </div>
      </div>
    </div>
  );
}

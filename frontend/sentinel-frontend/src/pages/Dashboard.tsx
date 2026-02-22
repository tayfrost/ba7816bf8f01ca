import Stepper from "../components/Stepper";
import { useMemo, useState } from "react";
import { useOnboarding } from "../state/onboarding";
import { countConnected, getConnectedProviders } from "../state/integrationRules";
import { computeRange } from "../state/timeRange";
import type { RangePreset } from "../state/timeRange";
import SimpleLineChart from "../components/SimpleLineChart";
import { useDashboardData } from "../hooks/useDashboardData";

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

export default function Dashboard() {
  const { signup, plan, integrations, reset } = useOnboarding();

  const [preset, setPreset] = useState<RangePreset>("week");
  const [customStart, setCustomStart] = useState("2026-01-01");
  const [customEnd, setCustomEnd] = useState("2026-02-20");

  const range = useMemo(() => {
    if (preset === "custom") return computeRange("custom", { start: customStart, end: customEnd });
    return computeRange(preset);
  }, [preset, customStart, customEnd]);

  const { status, error, series: metricSeries } = useDashboardData(range);

  const connectedCount = useMemo(() => countConnected(integrations), [integrations]);

  const connectedProviders = useMemo(() => getConnectedProviders(integrations), [integrations]);

  const riskScore = useMemo(() => generateMockRiskScore(connectedCount), [connectedCount]);

  const alerts = useMemo(() => generateMockAlerts(connectedProviders), [connectedProviders]);

  return (
    <div>
      <Stepper currentPath="/dashboard" />

      <div style={{ padding: 24 }}>
        <h1>Dashboard</h1>

        <section style={{ marginTop: 24 }}>
          <h2>Organisation Summary</h2>
          <p>
            <strong>Company:</strong> {signup?.companyName}
          </p>
          <p>
            <strong>Plan:</strong> {plan}
          </p>
          <p>
            <strong>Connected Providers:</strong> {connectedCount}
          </p>
        </section>

        <section style={{ marginTop: 32 }}>
          <h2>Time range</h2>

          <p style={{ marginTop: 8, opacity: 0.7 }}>
            Data status: <strong>{status}</strong>
            {error ? <> — {error}</> : null}
          </p>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 10 }}>
            <button onClick={() => setPreset("week")}>Week</button>
            <button onClick={() => setPreset("month")}>Month</button>
            <button onClick={() => setPreset("year")}>Year</button>
            <button onClick={() => setPreset("all")}>All Time</button>
            <button onClick={() => setPreset("custom")}>Custom</button>
          </div>

          {preset === "custom" && (
            <div style={{ marginTop: 12, display: "flex", gap: 12, alignItems: "center" }}>
              <label>
                Start:{" "}
                <input
                  type="date"
                  value={customStart}
                  onChange={(e) => setCustomStart(e.target.value)}
                />
              </label>
              <label>
                End:{" "}
                <input
                  type="date"
                  value={customEnd}
                  onChange={(e) => setCustomEnd(e.target.value)}
                />
              </label>
            </div>
          )}

          <p style={{ marginTop: 10, opacity: 0.8 }}>
            Showing: <strong>{range.start}</strong> → <strong>{range.end}</strong>
          </p>
        </section>

        <section style={{ marginTop: 32 }}>
          <h2>Risk Overview (Mock)</h2>
          <p>
            <strong>Current Risk Score:</strong> {riskScore}%
          </p>
          <p>Risk score is derived from connected data sources and behavioural signals.</p>
        </section>

        <section style={{ marginTop: 32 }}>
          <h2>Graphs (one line per chart)</h2>

          {metricSeries.map((s) => {
            const first = s.points[0];
            const last = s.points[s.points.length - 1];

            return (
              <div
                key={s.key}
                style={{
                  border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: 12,
                  padding: 14,
                  marginTop: 12,
                }}
              >
                <div style={{ fontWeight: 700 }}>{s.label}</div>
                <div style={{ opacity: 0.8, marginTop: 6 }}>
                  Start: {first?.value ?? "-"} | Latest: {last?.value ?? "-"}
                </div>

                <div style={{ marginTop: 12 }}>
                  <SimpleLineChart points={s.points} />
                </div>
              </div>
            );
          })}
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
          <button onClick={reset}>Reset demo state</button>
        </div>
      </div>
    </div>
  );
}
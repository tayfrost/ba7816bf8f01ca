import Stepper from "../components/Stepper";
import { useNavigate } from "react-router-dom";

export default function Usage() {
  const nav = useNavigate();

  return (
    <div>
      <Stepper currentPath="/usage" />

      <div style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
        <h1>How to use SentinelAI</h1>

        <p style={{ marginTop: 12, opacity: 0.85 }}>
          SentinelAI is a consent-based early warning system for burnout risk. Follow these steps to set up
          and interpret your organisation’s dashboard.
        </p>

        <h2 style={{ marginTop: 24 }}>Setup steps</h2>
        <ol style={{ marginTop: 10, lineHeight: 1.7 }}>
          <li>Connect your work accounts (Slack/Gmail/Outlook) via the Connect Accounts page.</li>
          <li>Open the Dashboard to view metrics and trends over time.</li>
          <li>Use Week/Month/Year/All Time/Custom ranges to explore patterns.</li>
          <li>Review alerts for potential risk signals and investigate context.</li>
        </ol>

        <h2 style={{ marginTop: 24 }}>Next</h2>
        <p style={{ marginTop: 10, opacity: 0.85 }}>
          When you're ready, go to the Dashboard to view organisation metrics.
        </p>

        <div style={{ marginTop: 18 }}>
          <button onClick={() => nav("/dashboard")}>Go to Dashboard</button>
        </div>
      </div>
    </div>
  );
}

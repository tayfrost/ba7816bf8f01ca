import { useNavigate } from "react-router-dom";
import Stepper from "../components/Stepper";
import { useOnboarding } from "../state/onboarding";

export default function ChoosePlan() {
  const navigate = useNavigate();
  const { setPlan } = useOnboarding();

  function selectPlan(plan: "free" | "paid") {
    setPlan(plan);
    navigate(`/signup?plan=${plan}`);
  }

  return (
    <div>
      <Stepper currentPath="/plan" />

      <div style={{ padding: 24 }}>
        <h1>Choose your plan</h1>

        <div style={{ display: "flex", gap: 16, marginTop: 24 }}>
          <div
            onClick={() => selectPlan("free")}
            style={{
              border: "1px solid #ddd",
              padding: 16,
              cursor: "pointer",
              width: 180,
            }}
          >
            <h3>Free</h3>
            <p>Basic monitoring</p>
          </div>

          <div
            onClick={() => selectPlan("paid")}
            style={{
              border: "1px solid #ddd",
              padding: 16,
              cursor: "pointer",
              width: 180,
            }}
          >
            <h3>Paid</h3>
            <p>Advanced analytics</p>
          </div>
        </div>
      </div>
    </div>
  );
}

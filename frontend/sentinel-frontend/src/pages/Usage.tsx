import Stepper from "../components/Stepper";
import { useOnboarding } from "../state/onboarding";

export default function Usage() {
  const { signup, plan } = useOnboarding();

  return (
    <div>
      <Stepper currentPath="/usage" />

      <div style={{ padding: 24 }}>
        <h1>Usage overview</h1>

        <p><strong>Company:</strong> {signup?.companyName}</p>
        <p><strong>Plan:</strong> {plan}</p>

        <p style={{ marginTop: 24 }}>
          Next steps: connect your communication tools and start monitoring wellbeing trends.
        </p>
      </div>
    </div>
  );
}

import Stepper from "../components/Stepper";

export default function ChoosePlan() {
  return (
    <div>
      <Stepper currentPath="/plan" />
      <div style={{ padding: 24 }}>
        <h1>Choose plan</h1>
        <p>Select Free or Paid.</p>
      </div>
    </div>
  );
}

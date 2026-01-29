import Stepper from "../components/Stepper";

export default function Payment() {
  return (
    <div>
      <Stepper currentPath="/payment" />
      <div style={{ padding: 24 }}>
        <h1>Payment details</h1>
        <p>Collect payment info (mock).</p>
      </div>
    </div>
  );
}

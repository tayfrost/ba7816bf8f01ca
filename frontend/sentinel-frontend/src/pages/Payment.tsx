import { useNavigate } from "react-router-dom";
import Stepper from "../components/Stepper";
import { useOnboarding } from "../state/onboarding";

export default function Payment() {
  const navigate = useNavigate();
  const { setPaymentSuccess } = useOnboarding();

  function handlePay() {
    setPaymentSuccess(true);
    navigate("/usage");
  }

  return (
    <div>
      <Stepper currentPath="/payment" />

      <div style={{ padding: 24, maxWidth: 400 }}>
        <h1>Payment details</h1>

        <input placeholder="Card number" style={{ width: "100%", marginBottom: 12 }} />
        <input placeholder="Expiry date" style={{ width: "100%", marginBottom: 12 }} />
        <input placeholder="CVC" style={{ width: "100%", marginBottom: 16 }} />

        <button onClick={handlePay}>Pay</button>
      </div>
    </div>
  );
}

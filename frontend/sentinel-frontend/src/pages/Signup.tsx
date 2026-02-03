import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Stepper from "../components/Stepper";
import { useOnboarding } from "../state/onboarding";

export default function Signup() {
  const navigate = useNavigate();
  const { setSignup } = useOnboarding();

  const [companyName, setCompanyName] = useState("");
  const [adminName, setAdminName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");

  function handleContinue() {
    if (!companyName || !adminName || !adminEmail) return;

    setSignup({
      companyName,
      adminName,
      adminEmail,
    });

    navigate("/plan");
  }

  return (
    <div>
      <Stepper currentPath="/signup" />

      <div style={{ padding: 24, maxWidth: 400 }}>
        <h1>Sign up</h1>

        <input
          placeholder="Company name"
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          style={{ display: "block", width: "100%", marginBottom: 12 }}
        />

        <input
          placeholder="Admin name"
          value={adminName}
          onChange={(e) => setAdminName(e.target.value)}
          style={{ display: "block", width: "100%", marginBottom: 12 }}
        />

        <input
          placeholder="Admin email"
          value={adminEmail}
          onChange={(e) => setAdminEmail(e.target.value)}
          style={{ display: "block", width: "100%", marginBottom: 16 }}
        />

        <button onClick={handleContinue}>Continue</button>
      </div>
    </div>
  );
}

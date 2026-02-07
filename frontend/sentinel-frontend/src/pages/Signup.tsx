import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Stepper from "../components/Stepper";
import Input from "../components/Input";
import Button from "../components/Button";
import AuthCard from "../components/AuthCard";
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
    <div className="min-h-screen pb-20 bg-transparent">
      <Stepper currentPath="/signup" />


      <div className="flex flex-col items-center mt-16 mb-12">
        <img 
          src="/logo-icon.png" 
          alt="SentinelAI Logo" 
          className="h-32 md:h-42 w-auto mb-6 drop-shadow-2xl" 
        />
        <img 
          src="/logo-text.png" 
          alt="SentinelAI" 
          className="h-10 md:h-14 w-auto opacity-90" 
        />
      </div>

      <AuthCard>
        <div className="space-y-6">
          <h2 className="text-2xl font-bold text-brand-deep text-center mb-8">
            Sign Up for an Account
          </h2>

          <Input
            label="Company Name"
            placeholder="e.g. Purpl Corp"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
          />

          <Input
            label="Admin Name"
            placeholder="e.g. Jane Doe"
            value={adminName}
            onChange={(e) => setAdminName(e.target.value)}
          />

          <Input
            label="Admin Email"
            type="email"
            placeholder="admin@company.com"
            value={adminEmail}
            onChange={(e) => setAdminEmail(e.target.value)}
          />

          <div className="pt-4">
            <Button variant="primary" onClick={handleContinue}>
              Continue
            </Button>
          </div>
        </div>
      </AuthCard>
    </div>
  );
}
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import Stepper from "../components/Stepper";
import Input from "../components/Input";
import Button from "../components/Button";
import AuthCard from "../components/AuthCard";
import { useOnboarding } from "../state/onboarding";

export default function Signup() {
  const navigate = useNavigate();

  const { setSignup, setPlan } = useOnboarding();

  const [searchParams] = useSearchParams();
  const selectedPlan = searchParams.get("plan") as "free" | "paid" | null;

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

    if (selectedPlan) {
      setPlan(selectedPlan);
    }

    navigate("/plan");
  }

  return (
    <div className="min-h-screen pb-20 bg-transparent font-sans">
      <Stepper currentPath="/signup" />

      {/* Hero Section */}
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

          <div className="text-center mb-8">
            <h2 className="text-3xl font-serif font-black text-brand-deep leading-tight">
              Create Your Account
            </h2>
            <p className="text-xs uppercase tracking-[0.2em] text-brand-deep/50 font-bold mt-2">
              Wellness | Protection | Support
            </p>
          </div>

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

          <div className="pt-4 space-y-6">
            <Button variant="primary" onClick={handleContinue}>
              Continue
            </Button>

            {/* Login Link Section */}
            <div className="text-center pt-2 border-t border-brand-deep/5">
              <p className="text-sm text-brand-deep/60">
                Already have an account?{" "}
                <button 
                  onClick={() => navigate("/login")}
                  className="text-brand-deep font-bold hover:underline underline-offset-4"
                >
                  Log In
                </button>
              </p>
            </div>
          </div>
        </div>
      </AuthCard>
    </div>
  );
}
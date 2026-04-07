import Stepper from "../components/Stepper";
import AuthCard from "../components/AuthCard";
import Button from "../components/Button";
import LandingHeader from "../components/LandingHeader";
import { useOnboarding } from "../state/onboarding";
import { useCompany } from "../hooks/useCompany";
import { getPlans } from "../api/plans";
import { useEffect, useState } from "react";

const PAYMENTS_URL = import.meta.env.VITE_PAYMENTS_URL;

export default function Payment() {
  const { plan, planInterval } = useOnboarding();
  const { company } = useCompany();
  const [planId, setPlanId] = useState<number | null>(null);

  const companyId = company?.company_id; 

  useEffect(() => {
    async function loadPlanId() {
      const plans = await getPlans();
      const match = plans.find(p =>
        plan === "free"
          ? p.plan_name.toLowerCase() === "free"
          : p.plan_name.toLowerCase() !== "free"
      );
      if (match) setPlanId(match.plan_id);
    }
    loadPlanId();
  }, [plan]);

  const handleCheckout = async () => {
    if (!company?.company_id || !planId) {
      alert("Missing company or plan");
      return;
    }

    try {
      const res = await fetch(`${PAYMENTS_URL}/api/v1/checkout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          company_id: company.company_id,
          plan_id: planId,
          interval: planInterval, 
        }),
      });

      const data = await res.json();

      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } 

    } catch (err) {
      console.error("Checkout failed", err);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-transparent font-sans overflow-y-auto">
      <LandingHeader />

      <div className="flex flex-col items-center mt-16 mb-12 shrink-0">
        <div className="mb-8 mt-12">
          <Stepper currentPath="/payment" />
        </div>

        <AuthCard>
          <div className="text-center mb-8">
            <h1 className="text-3xl font-serif font-black text-brand-deep leading-tight">
              Secure Payment
            </h1>
            <p className="text-brand-deep/60 mt-2">
              You will be redirected to Stripe to complete your payment securely.
            </p>
          </div>

          <div className="space-y-6">
            <div className="pt-4">
              <Button
                onClick={handleCheckout}
                variant="primary"
                disabled={!companyId || !planId}
              >
                {!companyId || !planId ? "Loading..." : "Proceed to Payment"}
              </Button>
            </div>
          </div>

          <p className="text-center text-[10px] text-brand-deep/40 uppercase tracking-[0.2em] font-bold mt-8">
            Payments are securely handled by Stripe
          </p>
        </AuthCard>
      </div>
    </div>
  );
}
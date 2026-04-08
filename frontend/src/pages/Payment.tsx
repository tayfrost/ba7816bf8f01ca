import Stepper from "../components/Stepper";
import AuthCard from "../components/AuthCard";
import Button from "../components/Button";
import LandingHeader from "../components/LandingHeader";
import { useOnboarding } from "../state/onboarding";
import { useCompany } from "../hooks/useCompany";
import { getPlans } from "../api/plans";
import { useEffect, useState } from "react";

const PAYMENTS_URL = import.meta.env.VITE_PAYMENTS_URL ?? "https://sentinelai.work";
console.log("[payment] PAYMENTS_URL:", PAYMENTS_URL);

export default function Payment() {
  console.log("[payment component] render init");
  const { plan, planInterval } = useOnboarding();
  const { company } = useCompany();
  const [planId, setPlanId] = useState<number | null>(null);

  const companyId = company?.company_id; 

  useEffect(() => {
    console.log("[payment component] mounted. companyId:", companyId);
    return () => console.log("[payment component] unmounted");
  }, [companyId]);

  useEffect(() => {
    async function loadPlanId() {
      console.log("[payment] loading plans, selected plan:", plan);
      try {
        const plans = await getPlans();
        console.log("[payment] plans fetched:", plans.map(p => ({ id: p.plan_id, name: p.plan_name })));
        const match = plans.find(p =>
          plan === "free"
            ? p.plan_name.toLowerCase() === "free"
            : p.plan_name.toLowerCase() !== "free"
        );
        console.log("[payment] matched plan:", match ?? "NONE");
        if (match) setPlanId(match.plan_id);
      } catch (err) {
        console.error("[payment] failed to load plans:", err);
      }
    }
    loadPlanId();
  }, [plan]);

  const handleCheckout = async () => {
    console.log("[checkout] handleCheckout start — companyId:", company?.company_id, "planId:", planId, "interval:", planInterval);

    if (!company?.company_id || !planId) {
      console.warn("[checkout] aborted — missing companyId:", company?.company_id, "or planId:", planId);
      alert("Missing company or plan");
      return;
    }

    const endpoint = `${PAYMENTS_URL}/api/v1/checkout`;
    console.log("[checkout] POST", endpoint);

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_id: company.company_id,
          plan_id: planId,
          interval: planInterval,
        }),
      });

      console.log("[checkout] response status:", res.status);

      if (!res.ok) {
        const errText = await res.text().catch(() => "");
        console.error("[checkout] non-ok response:", res.status, errText);
        alert(`Payment error ${res.status}: ${errText}`);
        return;
      }

      const data = await res.json();
      console.log("[checkout] response data:", data);

      if (data.checkout_url) {
        console.log("[checkout] redirecting to Stripe:", data.checkout_url);
        window.location.href = data.checkout_url;
      } else {
        console.error("[checkout] no checkout_url in response", data);
        alert("No checkout URL returned. Check console for details.");
      }

    } catch (err) {
      console.error("[checkout] fetch failed:", err);
      alert("Network error during checkout. Check console.");
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
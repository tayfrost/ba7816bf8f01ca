import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCompany } from "../hooks/useCompany";
import { getPlans } from "../api";
import type { Plan } from "../api/plans";

/**
 * Blocks access to a route when the company is on the free plan.
 * Relies on /companies/me (plan_id) cross-referenced with /api/v1/plans (price).
 * Must be used inside RequireAuth so company data is already accessible.
 */
export default function RequirePaidPlan({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const { company, status: companyStatus } = useCompany();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [plansStatus, setPlansStatus] = useState<"idle" | "loading" | "done">("idle");

  useEffect(() => {
    setPlansStatus("loading");
    getPlans()
      .then((p) => { setPlans(p); setPlansStatus("done"); })
      .catch(() => setPlansStatus("done")); // on error, allow through
  }, []);

  const loading =
    companyStatus === "idle" ||
    companyStatus === "loading" ||
    plansStatus !== "done";

  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          background: "linear-gradient(to bottom, #20022bfd, #1a011d)",
          color: "white",
          fontFamily: "'Outfit', 'Inter', sans-serif",
        }}
      >
        Checking plan...
      </div>
    );
  }

  const companyPlan = plans.find((p) => p.plan_id === company?.plan_id);
  const isFree = !companyPlan || companyPlan.plan_cost_pennies === 0;

  if (isFree) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          background: "linear-gradient(to bottom, #20022bfd, #1a011d)",
          color: "white",
          fontFamily: "'Outfit', 'Inter', sans-serif",
          textAlign: "center",
          padding: "2rem",
        }}
      >
        <div>
          <p style={{ fontSize: "3rem", marginBottom: "1rem" }}>🔒</p>
          <h2
            style={{
              fontSize: "1.75rem",
              fontWeight: 900,
              marginBottom: "0.75rem",
              letterSpacing: "-0.5px",
            }}
          >
            Paid Plan Required
          </h2>
          <p style={{ opacity: 0.65, marginBottom: "2rem", maxWidth: "360px", lineHeight: 1.6 }}>
            Gmail member registration is available on paid plans. Ask your team admin to upgrade.
          </p>
          <button
            onClick={() => navigate("/plan")}
            style={{
              background: "rgba(227,141,38,0.18)",
              color: "#e38d26",
              border: "1px solid rgba(227,141,38,0.4)",
              borderRadius: "12px",
              padding: "12px 28px",
              fontSize: "13px",
              fontWeight: 900,
              cursor: "pointer",
              letterSpacing: "1px",
              textTransform: "uppercase",
            }}
          >
            View Plans
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useOnboarding } from "../state/onboarding";
import { hasAnyIntegrationConnected } from "../state/integrationRules";

export default function RequireOnboarding({ children }: { children: React.ReactNode }) {
  const { signup, plan, paymentSuccess, integrations } = useOnboarding();
  const location = useLocation();
  const hasStripeSessionReturn =
    location.pathname === "/connect-accounts" &&
    new URLSearchParams(location.search).has("session_id");

  if (!signup) return <Navigate to="/signup" replace />;

  // Only paid plans must complete payment
  if (plan === "paid" && !paymentSuccess && !hasStripeSessionReturn) {
    console.log("[RequireOnboarding] Redirecting to /payment -> plan=paid, paymentSuccess=false");
    return <Navigate to="/payment" replace />;
  }

  const anyConnected = hasAnyIntegrationConnected(integrations);

  // allow visiting connect page itself even when nothing is connected
  if (!anyConnected && location.pathname !== "/connect-accounts") {
    return <Navigate to="/connect-accounts" replace />;
  }

  return <>{children}</>;
}
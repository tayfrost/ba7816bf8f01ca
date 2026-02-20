import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useOnboarding } from "../state/onboarding";
import { hasAnyIntegrationConnected } from "../state/integrationRules";

export default function RequireOnboarding({ children }: { children: React.ReactNode }) {
  const { signup, plan, paymentSuccess, integrations } = useOnboarding();
  const location = useLocation();

  if (!signup) return <Navigate to="/signup" replace />;
  if (!plan) return <Navigate to="/plan" replace />;

  // Only paid plans must complete payment
  if (plan === "paid" && !paymentSuccess) return <Navigate to="/payment" replace />;

  const anyConnected = hasAnyIntegrationConnected(integrations);

  // allow visiting connect page itself even when nothing is connected
  if (!anyConnected && location.pathname !== "/connect-accounts") {
    return <Navigate to="/connect-accounts" replace />;
  }

  return <>{children}</>;
}
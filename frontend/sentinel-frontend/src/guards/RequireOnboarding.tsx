import React from "react"; 
import { Navigate, useLocation } from "react-router-dom";
import { useOnboarding } from "../state/onboarding";

export default function RequireOnboarding({ children }: { children: React.ReactNode }) {
  const { signup, plan, paymentSuccess, integrations } = useOnboarding();
  const location = useLocation();

  if (!signup) return <Navigate to="/signup" replace />;
  if (!plan) return <Navigate to="/plan" replace />;
  
  // fix: ensures free users don't get stuck at payment
  if (plan === "paid" && !paymentSuccess) return <Navigate to="/payment" replace />;

  // fix: prevents crash if integrations is undefined
  const anyConnected = (integrations ?? []).some((i: any) => i.connected);

  if (!anyConnected && location.pathname !== "/connect-accounts") {
    return <Navigate to="/connect-accounts" replace />;
  }

  return <>{children}</>;
}
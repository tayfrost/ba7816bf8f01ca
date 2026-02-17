import { Navigate, useLocation } from "react-router-dom";
import { useOnboarding } from "../state/onboarding";

export default function RequireOnboarding({ children }: { children: JSX.Element }) {
  const { signup, plan, paymentSuccess, integrations } = useOnboarding();
  const location = useLocation();

  if (!signup) return <Navigate to="/signup" replace />;
  if (!plan) return <Navigate to="/plan" replace />;
  if (!paymentSuccess) return <Navigate to="/payment" replace />;

  const anyConnected = integrations.some((i) => i.connected);

  //Allow the connect accounts page itself even if not connected yet
  if (!anyConnected && location.pathname !== "/connect-accounts") {
    return <Navigate to="/connect-accounts" replace />;
  }

  return children;
}

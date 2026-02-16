import { Navigate, useLocation } from "react-router-dom";
import { useOnboarding } from "../state/onboarding";

export default function RequireOnboarding({ children }: { children: JSX.Element }) {
  const { signup, plan, paymentSuccess, accountConnected } = useOnboarding();
  const location = useLocation();
  const path = location.pathname;

  if (!signup) return <Navigate to="/signup" replace />;
  if (!plan) return <Navigate to="/plan" replace />;
  if (!paymentSuccess) return <Navigate to="/payment" replace />;

  //Allow the connect accounts page itself even if not connected yet
  if (!accountsConnected && path !== "/connect-accounts") {
    return <Navigate to="/connect-accounts" replace />;
  }

  return children;
}

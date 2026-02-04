import { Navigate } from "react-router-dom";
import { useOnboarding } from "../state/onboarding";

export default function RequireOnboarding({ children }: { children: JSX.Element }) {
  const { signup, plan } = useOnboarding();

  if (!signup) return <Navigate to="/signup" replace />;
  if (!plan) return <Navigate to="/plan" replace />;

  return children;
}

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Input from "../components/Input";
import Button from "../components/Button";
import AuthCard from "../components/AuthCard";
import { login, getIntegrations, getMe } from "../api";
import { useOnboarding } from "../state/onboarding";
import type { Provider } from "../state/onboarding";
import { SESSION_DAYS_KEY, SESSION_DAYS_DEFAULT } from "../components/settings/SecuritySettings";

export default function Login() {
  const navigate = useNavigate();
  const { setIntegrationConnected, setSignup, setPlan } = useOnboarding();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleLogin() {
    if (!email || !password) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const rememberDays = (() => {
        try {
          const raw = localStorage.getItem(SESSION_DAYS_KEY);
          const parsed = raw ? parseInt(raw, 10) : NaN;
          return [1, 7, 30].includes(parsed) ? parsed : SESSION_DAYS_DEFAULT;
        } catch {
          return SESSION_DAYS_DEFAULT;
        }
      })();

      const res = await login({ email, password, remember_days: rememberDays });
      localStorage.setItem("sentinel_access_token", res.access_token);

      // Sync onboarding state from server to prevent stale localStorage
      // causing wrong redirects for returning users on a fresh browser.
      try {
        const [me, apiIntegrations] = await Promise.all([getMe(), getIntegrations()]);

        // Populate signup so RequireOnboarding doesn't redirect to /signup
        setSignup({
          companyName: "",   // will be overwritten by useCompany on next page
          adminName: me.display_name || me.email,
          adminEmail: me.email,
        });

        // Sync actual integration connected state
        apiIntegrations.forEach((i) => {
          setIntegrationConnected(i.provider as Provider, i.connected);
        });
      } catch {
        // Non-fatal: ensure signup is populated even if getMe fails
        setSignup({ companyName: "", adminName: email, adminEmail: email });
      }

      // Always set plan so RequireOnboarding doesn't redirect to /plan
      setPlan("free");

      navigate("/dashboard");
    } catch (err) {
      setError("Login failed. Please check your credentials.");
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen pb-20 bg-transparent font-sans">
      <div className="flex flex-col items-center mt-24 mb-12">
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
              Welcome Back
            </h2>
            <p className="text-xs uppercase tracking-[0.2em] text-brand-deep/50 font-bold mt-2">
              Wellness | Protection | Support
            </p>
          </div>

          <Input
            label="Admin Email"
            type="email"
            placeholder="admin@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <Input
            label="Password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error && (
            <p className="text-sm font-semibold text-red-600 text-center">
              {error}
            </p>
          )}

          <div className="pt-4 space-y-6">
            <Button variant="primary" onClick={handleLogin} disabled={isSubmitting}>
              {isSubmitting ? "Logging In..." : "Log In"}
            </Button>

            <div className="text-center pt-2 border-t border-brand-deep/5">
              <p className="text-sm text-brand-deep/60">
                Don't have an account?{" "}
                <button
                  onClick={() => navigate("/plan")}
                  className="text-brand-deep font-bold hover:underline underline-offset-4"
                >
                  Get Started
                </button>
              </p>
            </div>
          </div>
        </div>
      </AuthCard>
    </div>
  );
}
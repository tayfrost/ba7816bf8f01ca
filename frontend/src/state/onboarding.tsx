import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type PlanType = "free" | "paid";
export type PlanInterval = "month" | "year";

export type SignupData = {
  companyName: string;
  adminName: string;
  adminEmail: string;
};

export type Provider = "slack" | "gmail";

export type Integration = {
  provider: Provider;
  connected: boolean;
  connectedAt?: string;
};

type OnboardingState = {
  signup: SignupData | null;
  plan: PlanType | null;
  paymentSuccess: boolean;
  companyId: string | null;
  planInterval: PlanInterval;
  integrations: Integration[];

  setSignup: (data: SignupData) => void;
  setPlan: (plan: PlanType) => void;
  setPaymentSuccess: (v: boolean) => void;
  setIntegrationConnected: (provider: Provider, connected: boolean) => void;
  setCompanyId: (id: string) => void;
  setPlanInterval: (interval: PlanInterval) => void;
  reset: () => void;
};

const OnboardingContext = createContext<OnboardingState | undefined>(undefined);

const STORAGE_KEY = "sentinel_onboarding_v1";

type Persisted = {
  signup: SignupData | null;
  plan: PlanType | null;
  paymentSuccess: boolean;
  companyId: string | null;
  integrations: Integration[];
};

const DEFAULT_INTEGRATIONS: Integration[] = [
  { provider: "slack", connected: false },
  { provider: "gmail", connected: false },
];

function loadPersisted(): Persisted {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { signup: null, plan: null, paymentSuccess: false, companyId: null, integrations: DEFAULT_INTEGRATIONS };
    }
    const parsed = JSON.parse(raw) as Partial<Persisted>;
    return {
      signup: parsed.signup ?? null,
      plan: (parsed.plan as PlanType) ?? null,
      paymentSuccess: parsed.paymentSuccess ?? false,
      companyId: parsed.companyId ?? null,
      integrations: parsed.integrations ?? DEFAULT_INTEGRATIONS,
    };
  } catch {
    return { signup: null, plan: null, paymentSuccess: false, companyId: null, integrations: DEFAULT_INTEGRATIONS };
  }
}

function savePersisted(p: Persisted) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(p));
  } catch {}
}

export function OnboardingProvider({ children }: { children: React.ReactNode }) {
  const initial = loadPersisted();

  const [signup, setSignupState] = useState<SignupData | null>(initial.signup);
  const [plan, setPlanState] = useState<PlanType | null>(initial.plan);
  const [paymentSuccess, setPaymentSuccessState] = useState<boolean>(initial.paymentSuccess);
  const [companyId, setCompanyIdState] = useState<string | null>(initial.companyId);
  const [integrations, setIntegrations] = useState<Integration[]>(initial.integrations);
  const [planInterval, setPlanIntervalState] = useState<PlanInterval>("month");

  useEffect(() => {
    savePersisted({ signup, plan, paymentSuccess, companyId, integrations });
  }, [signup, plan, paymentSuccess, companyId, integrations]);

  // Stable reference: setIntegrations from useState never changes identity,
  // so this callback is created once and never causes re-renders in consumers.
  const setIntegrationConnected = useCallback((provider: Provider, connected: boolean) => {
    setIntegrations((prev) =>
      prev.map((i) =>
        i.provider === provider
          ? { ...i, connected, connectedAt: connected ? new Date().toISOString() : undefined }
          : i
      )
    );
  }, []);

  const value = useMemo<OnboardingState>(
    () => ({
      signup,
      plan,
      paymentSuccess,
      integrations,
      companyId,
      planInterval,

      setCompanyId: (id) => setCompanyIdState(id),
      setPlanInterval: (i) => setPlanIntervalState(i),
      setSignup: (data) => setSignupState(data),
      setPlan: (p) => setPlanState(p),
      setPaymentSuccess: (v) => setPaymentSuccessState(v),

      setIntegrationConnected,

      reset: () => {
        setSignupState(null);
        setPlanState(null);
        setPaymentSuccessState(false);
        setIntegrations(DEFAULT_INTEGRATIONS);
        setCompanyIdState(null);
        setPlanIntervalState("month");
        try {
          localStorage.removeItem(STORAGE_KEY);
          localStorage.removeItem("sentinel_access_token");
        } catch {}
      },
    }),
    [signup, plan, paymentSuccess, companyId, integrations, planInterval, setIntegrationConnected]
  );

  return <OnboardingContext.Provider value={value}>{children}</OnboardingContext.Provider>;
}

export function useOnboarding() {
  const ctx = useContext(OnboardingContext);
  if (!ctx) throw new Error("useOnboarding must be used within OnboardingProvider");
  return ctx;
}
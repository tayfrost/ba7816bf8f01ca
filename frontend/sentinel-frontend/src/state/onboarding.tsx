import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

export type PlanType = "free" | "paid";

export type SignupData = {
  companyName: string;
  adminName: string;
  adminEmail: string;
};

export type Provider = "slack" | "gmail" | "outlook";

export type Integration = {
  provider: Provider;
  connected: boolean;
  connectedAt?: string;
};

type OnboardingState = {
  signup: SignupData | null;
  plan: PlanType | null;
  paymentSuccess: boolean;

  integrations: Integration[];
  setSignup: (data: SignupData) => void;
  setPlan: (plan: PlanType) => void;
  setPaymentSuccess: (v: boolean) => void;
  setIntegrationConnected: (provider: Provider, connected: boolean) => void;

  reset: () => void;
};

const OnboardingContext = createContext<OnboardingState | undefined>(undefined);

const STORAGE_KEY = "sentinel_onboarding_v1";

type Persisted = {
  signup: SignupData | null;
  plan: PlanType | null;
  paymentSuccess: boolean;
  integrations: Integration[];
};

const DEFAULT_INTEGRATIONS: Integration[] = [
  { provider: "slack", connected: false },
  { provider: "gmail", connected: false },
  { provider: "outlook", connected: false },
];

function loadPersisted(): Persisted {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { signup: null, plan: null, paymentSuccess: false, integrations: DEFAULT_INTEGRATIONS };
    }
    const parsed = JSON.parse(raw) as Partial<Persisted>;
    return {
      signup: parsed.signup ?? null,
      plan: (parsed.plan as PlanType) ?? null,
      paymentSuccess: parsed.paymentSuccess ?? false,
      integrations: parsed.integrations ?? DEFAULT_INTEGRATIONS,
    };
  } catch {
    return { signup: null, plan: null, paymentSuccess: false, integrations: DEFAULT_INTEGRATIONS };
  }
}

function savePersisted(p: Persisted) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(p));
  } catch {
    // ignore
  }
}

export function OnboardingProvider({ children }: { children: React.ReactNode }) {
  const initial = loadPersisted();

  const [signup, setSignupState] = useState<SignupData | null>(initial.signup);
  const [plan, setPlanState] = useState<PlanType | null>(initial.plan);
  const [paymentSuccess, setPaymentSuccessState] = useState<boolean>(initial.paymentSuccess);
  const [integrations, setIntegrations] = useState<Integration[]>(initial.integrations);

  useEffect(() => {
    savePersisted({ signup, plan, paymentSuccess, integrations });
  }, [signup, plan, paymentSuccess, integrations]);

  const value = useMemo<OnboardingState>(
    () => ({
      signup,
      plan,
      paymentSuccess,
      integrations,

      setSignup: (data) => setSignupState(data),
      setPlan: (p) => setPlanState(p),
      setPaymentSuccess: (v) => setPaymentSuccessState(v),

      setIntegrationConnected: (provider, connected) => {
        setIntegrations((prev) =>
          prev.map((i) =>
            i.provider === provider
              ? { ...i, connected, connectedAt: connected ? new Date().toISOString() : undefined }
              : i
          )
        );
      },

      reset: () => {
        setSignupState(null);
        setPlanState(null);
        setPaymentSuccessState(false);
        setIntegrations(DEFAULT_INTEGRATIONS);

        try {
          localStorage.removeItem(STORAGE_KEY);
        } catch {
          // ignore
        }
      },
    }),
    [signup, plan, paymentSuccess, integrations]
  );

  return <OnboardingContext.Provider value={value}>{children}</OnboardingContext.Provider>;
}

export function useOnboarding() {
  const ctx = useContext(OnboardingContext);
  if (!ctx) throw new Error("useOnboarding must be used within OnboardingProvider");
  return ctx;
}
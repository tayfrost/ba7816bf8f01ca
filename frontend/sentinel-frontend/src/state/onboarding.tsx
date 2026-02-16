import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

export type PlanType = "free" | "paid";

export type SignupData = {
  companyName: string;
  adminName: string;
  adminEmail: string;
};

type OnboardingState = {
  signup: SignupData | null;
  plan: PlanType | null;
  paymentSuccess: boolean;
  accountsConnected: boolean;

  setSignup: (data: SignupData) => void;
  setPlan: (plan: PlanType) => void;
  setPaymentSuccess: (v: boolean) => void;
  setAccountsConnected: (v: boolean) => void;

  reset: () => void;
};

const STORAGE_KEY = "sentinel_onboarding_v1";

type Persisted = {
  signup: SignupData | null;
  plan: PlanType | null;
  paymentSuccess: boolean;
  accountsConnected: boolean;
};

function loadPersisted(): Persisted {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { signup: null, plan: null, paymentSuccess: false, accountsConnected: false };
    }
    const parsed = JSON.parse(raw) as Partial<Persisted>;
    return {
      signup: parsed.signup ?? null,
      plan: (parsed.plan as PlanType) ?? null,
      paymentSuccess: parsed.paymentSuccess ?? false,
      accountsConnected: parsed.accountsConnected ?? false,
    };
  } catch {
    return { signup: null, plan: null, paymentSuccess: false, accountsConnected: false };
  }
}

function savePersisted(p: Persisted) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(p));
  } catch {
    // ignore
  }
}

const OnboardingContext = createContext<OnboardingState | undefined>(undefined);

export function OnboardingProvider({ children }: { children: React.ReactNode }) {
  const initial = loadPersisted();

  const [signup, setSignupState] = useState<SignupData | null>(initial.signup);
  const [plan, setPlanState] = useState<PlanType | null>(initial.plan);
  const [paymentSuccess, setPaymentSuccessState] = useState<boolean>(initial.paymentSuccess);
  const [accountsConnected, setAccountsConnectedState] = useState<boolean>(initial.accountsConnected);

  useEffect(() => {
    savePersisted({ signup, plan, paymentSuccess, accountsConnected });
  }, [signup, plan, paymentSuccess, accountsConnected]);

  const value = useMemo<OnboardingState>(
    () => ({
      signup,
      plan,
      paymentSuccess,
      accountsConnected,

      setSignup: (data) => setSignupState(data),
      setPlan: (p) => setPlanState(p),
      setPaymentSuccess: (v) => setPaymentSuccessState(v),
      setAccountsConnected: (v) => setAccountsConnectedState(v),

      reset: () => {
        setSignupState(null);
        setPlanState(null);
        setPaymentSuccessState(false);
        setAccountsConnectedState(false);
        savePersisted({ signup: null, plan: null, paymentSuccess: false, accountsConnected: false });
      },
    }),
    [signup, plan, paymentSuccess, accountsConnected]
  );

  return <OnboardingContext.Provider value={value}>{children}</OnboardingContext.Provider>;
}

export function useOnboarding() {
  const ctx = useContext(OnboardingContext);
  if (!ctx) throw new Error("useOnboarding must be used within OnboardingProvider");

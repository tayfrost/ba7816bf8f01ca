import React, { createContext, useContext, useMemo, useState } from "react";

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
  setSignup: (data: SignupData) => void;
  setPlan: (plan: PlanType) => void;
  setPaymentSuccess: (v: boolean) => void;
  reset: () => void;
};

const OnboardingContext = createContext<OnboardingState | undefined>(undefined);

export function OnboardingProvider({ children }: { children: React.ReactNode }) {
  const [signup, setSignupState] = useState<SignupData | null>(null);
  const [plan, setPlanState] = useState<PlanType | null>(null);
  const [paymentSuccess, setPaymentSuccessState] = useState(false);

  const value = useMemo<OnboardingState>(
    () => ({
      signup,
      plan,
      paymentSuccess,
      setSignup: (data) => setSignupState(data),
      setPlan: (p) => setPlanState(p),
      setPaymentSuccess: (v) => setPaymentSuccessState(v),
      reset: () => {
        setSignupState(null);
        setPlanState(null);
        setPaymentSuccessState(false);
      },
    }),
    [signup, plan, paymentSuccess]
  );

  return <OnboardingContext.Provider value={value}>{children}</OnboardingContext.Provider>;
}

export function useOnboarding() {
  const ctx = useContext(OnboardingContext);
  if (!ctx) throw new Error("useOnboarding must be used within OnboardingProvider");
  return ctx;
}

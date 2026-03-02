import { SignupData, PlanType, Integration } from "./onboarding";

export type NextStep = "/signup" | "/plan" | "/payment" | "/connect-accounts" | "/usage";

export function getNextStep(args: {
  signup: SignupData | null;
  plan: PlanType | null;
  paymentSuccess: boolean;
  integrations: Integration[];
}): NextStep {
  if (!args.signup) return "/signup";
  if (!args.plan) return "/plan";
  if (!args.paymentSuccess) return "/payment";
  if (!args.integrations.some(i => i.connected)) return "/connect-accounts";
  return "/usage";
}

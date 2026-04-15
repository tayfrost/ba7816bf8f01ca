import { apiFetch } from "./client";

export type Plan = {
  plan_id: number;
  plan_name: string;
  plan_cost_pennies: number;
  currency: string;
  max_employees: number;
  stripe_price_id_monthly: string | null;
  stripe_price_id_yearly: string | null;
};

export async function getPlans(): Promise<Plan[]> {
  try {
    const plans = await apiFetch<Plan[]>("/plans");
    return plans ?? [];
  } catch (err) {
    console.error("Failed to fetch plans:", err);
    return [];
  }
}
import { apiFetch } from "./client";

export type Incident = {
  message_id: string;        // real DB UUID
  incident_id: number;       // display row number only
  company_id: number;
  team_id: string;
  slack_user_id: string;
  message_ts: string;
  created_at: string;
  channel_id: string;
  raw_message_text: { text?: string } | null;
  class_reason: string;
  recommendation?: string;
};

export type IncidentStats = {
  total: number;
  by_reason: Record<string, number>;
};

export async function getIncidents(skip = 0, limit = 20): Promise<Incident[]> {
  return apiFetch<Incident[]>(`/incidents?skip=${skip}&limit=${limit}`);
}

export async function getIncidentStats(): Promise<IncidentStats> {
  return apiFetch<IncidentStats>("/incidents/stats");
}
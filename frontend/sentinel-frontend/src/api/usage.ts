import { apiFetch } from "./client";

export type SeriesPoint = { date: string; value: number };

export type Series = {
  key: string;
  label: string;
  points: SeriesPoint[];
};

export type UsageResponse = {
  range: { start: string; end: string };
  series: Series[];
};

export type UsageQuery = {
  start: string;
  end: string;
  metrics?: string[]; // e.g. ["riskScore","messagesFlagged","overtimeIndex"]
};

function buildQuery(q: UsageQuery) {
  const params = new URLSearchParams();
  params.set("start", q.start);
  params.set("end", q.end);
  if (q.metrics && q.metrics.length > 0) {
    params.set("metrics", q.metrics.join(","));
  }
  return params.toString();
}

export async function getUsage(q: UsageQuery): Promise<UsageResponse> {
  const query = buildQuery(q);
  return apiFetch<UsageResponse>(`/usage?${query}`);
}
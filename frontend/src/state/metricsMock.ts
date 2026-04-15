import { enumerateDays } from "./timeRange";

export type LinePoint = { date: string; value: number };

export type MetricKey =
  | "depression"
  | "burnout"
  | "stress"
  | "harassment"
  | "suicidal_ideation";

export type MetricSeries = {
  key: MetricKey;
  label: string;
  points: LinePoint[];
};

const CATEGORY_LABELS: Record<MetricKey, string> = {
  depression: "Depression",
  burnout: "Burnout",
  stress: "Stress",
  harassment: "Harassment",
  suicidal_ideation: "Suicidal ideation",
};

function seededRandom(seed: number) {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

export function makeSeries(range: { start: string; end: string }, key: MetricKey): MetricSeries {
  const days = enumerateDays(range.start, range.end);
  const points = days.map((d, i) => {
    const baseSeed = Number(d.replaceAll("-", "")) + key.length;
    const r = seededRandom(baseSeed + i);
    const value = Math.round(r * 1000) / 1000; // 0–1 score range
    return { date: d, value };
  });

  return { key, label: CATEGORY_LABELS[key], points };
}

export function makeAllSeries(range: { start: string; end: string }): MetricSeries[] {
  return (Object.keys(CATEGORY_LABELS) as MetricKey[]).map((key) =>
    makeSeries(range, key)
  );
}

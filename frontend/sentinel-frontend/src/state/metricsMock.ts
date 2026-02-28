import { enumerateDays } from "./timeRange";

export type LinePoint = { date: string; value: number };

export type MetricKey = "riskScore" | "messagesFlagged" | "overtimeIndex";

export type MetricSeries = {
  key: MetricKey;
  label: string;
  points: LinePoint[];
};

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function seededRandom(seed: number) {
  // deterministic-ish generator
  let x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

export function makeSeries(range: { start: string; end: string }, key: MetricKey): MetricSeries {
  const days = enumerateDays(range.start, range.end);
  const points = days.map((d, i) => {
    const baseSeed = d.split("-").join("") as any;
    const r = seededRandom(Number(baseSeed) + i);
    let value = 0;

    if (key === "riskScore") value = clamp(Math.round(30 + r * 60), 0, 100);
    if (key === "messagesFlagged") value = clamp(Math.round(r * 20), 0, 30);
    if (key === "overtimeIndex") value = clamp(Math.round(10 + r * 40), 0, 100);

    return { date: d, value };
  });

  const label =
    key === "riskScore" ? "Risk score" :
    key === "messagesFlagged" ? "Flagged messages" :
    "Overtime index";

  return { key, label, points };
}

export function makeAllSeries(range: { start: string; end: string }): MetricSeries[] {
  return [
    makeSeries(range, "riskScore"),
    makeSeries(range, "messagesFlagged"),
    makeSeries(range, "overtimeIndex"),
  ];
}
import { useEffect, useState } from "react";
import type { DateRange } from "../state/timeRange";
import { enumerateDays } from "../state/timeRange";
import { getUsage } from "../api";
import type { Series, SeriesPoint } from "../api";
import { makeAllSeries } from "../state/metricsMock";
import { dashboardDebug, dashboardDebugError } from "../utils/dashboardDebug";

type Status = "idle" | "loading" | "success" | "error";

const IS_MOCK = import.meta.env.VITE_USE_MOCKS === "true";

// Shown while waiting for real data — replaced automatically once polling picks up actual points
const PLACEHOLDER_SERIES = [
  { key: "depression", label: "Depression", points: [] },
  { key: "burnout", label: "Burnout", points: [] },
  { key: "stress", label: "Stress", points: [] },
  { key: "harassment", label: "Harassment", points: [] },
  { key: "suicidal_ideation", label: "Suicidal ideation", points: [] },
] as import("../api").Series[];

/**
 * Fill dates with 0 for the prefix of the window (before the first real data point).
 * The suffix (after the last real data point) is left as-is — filling it with zeros
 * would drag down the moving average for the most recent days.
 */
function fillRangeGaps(series: Series[], start: string, end: string): Series[] {
  const allDates = enumerateDays(start, end);
  return series.map((s) => {
    const pointMap = new Map(s.points.map((p) => [p.date, p.value]));

    // Find the last date that has a real data point
    const lastRealDate = s.points.length > 0
      ? s.points.reduce((latest, p) => (p.date > latest ? p.date : latest), s.points[0].date)
      : null;

    const points: SeriesPoint[] = allDates
      .filter((date) => date <= (lastRealDate ?? start))  // only prefix + real range
      .map((date) => ({
        date,
        value: pointMap.get(date) ?? 0,  // real value or 0 for prefix gaps
      }));

    // Append suffix points that have real data (no forced zeros)
    allDates
      .filter((date) => lastRealDate && date > lastRealDate && pointMap.has(date))
      .forEach((date) => points.push({ date, value: pointMap.get(date)! }));

    return { ...s, points };
  });
}

function normalizeGraphValue(value: number, targetMax: number = 10): number {
  let normalized = value;
  let guard = 0;

  while (Math.abs(normalized) > targetMax && guard < 8) {
    normalized /= 10;
    guard += 1;
  }

  return Math.round(normalized * 10000) / 10000;
}

function normalizeGraphSeries(series: Series[], targetMax: number = 10): Series[] {
  return series.map((s) => ({
    ...s,
    points: s.points.map((point) => ({
      ...point,
      value: normalizeGraphValue(point.value, targetMax),
    })),
  }));
}

// Frontend smoothing commented out — backend already applies 3-day rolling average.
// Double-smoothing caused excessive peak flattening. Uncomment to restore if needed.
// function smoothPoints(points: SeriesPoint[], window: number = 7): SeriesPoint[] {
//   return points.map((p, i) => {
//     const start = Math.max(0, i - window + 1);
//     const chunk = points.slice(start, i + 1);
//     const avg = chunk.reduce((sum, pt) => sum + pt.value, 0) / chunk.length;
//     return { date: p.date, value: Math.round(avg * 10) / 10 };
//   });
// }
// function smoothSeries(series: Series[], window: number = 7): Series[] {
//   return series.map((s) => ({ ...s, points: smoothPoints(s.points, window) }));
// }

export function useDashboardData(range: DateRange) {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [series, setSeries] = useState<Series[]>(PLACEHOLDER_SERIES);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setStatus("loading");
      setError(null);

      try {
        const res = await getUsage({ start: range.start, end: range.end });
        if (cancelled) return;

        dashboardDebug("useDashboardData", "raw-usage-response", res);

        const fetched = res?.series ?? [];
        // Fill prefix gaps with 0, leaving suffix as-is (backend applies 3-day rolling avg)
        // Frontend smoothing commented out — backend already smooths; double-smoothing distorted peaks
        const transformed = fetched.length > 0
          ? /* smoothSeries( */ fillRangeGaps(fetched, range.start, range.end) /* ) */
          : PLACEHOLDER_SERIES;
        const normalized = normalizeGraphSeries(transformed, 10);
        dashboardDebug("useDashboardData", "raw-incident-score-series", transformed);
        dashboardDebug("useDashboardData", "normalized-incident-score-series", normalized);
        setSeries(normalized);
        setStatus("success");
      } catch (e) {
        if (cancelled) return;

        console.error(e);
        dashboardDebugError("useDashboardData", "usage-payload-failed", e, { range, isMockEnv: IS_MOCK });

        if (IS_MOCK) {
          const mocked = /* smoothSeries( */ makeAllSeries(range) /* ) */;
          const normalizedMocked = normalizeGraphSeries(mocked, 10);
          dashboardDebug("useDashboardData", "raw-incident-score-series", mocked);
          dashboardDebug("useDashboardData", "normalized-incident-score-series", normalizedMocked);
          setSeries(normalizedMocked);
          setStatus("success");
          return;
        }

        // On error, keep current series (placeholder or real) and surface the error
        setStatus("error");
        setError("Failed to load dashboard metrics.");
      }
    }

    run();

    const interval = setInterval(run, 60_000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [range]);

  return { status, error, series, isMock: IS_MOCK };
}

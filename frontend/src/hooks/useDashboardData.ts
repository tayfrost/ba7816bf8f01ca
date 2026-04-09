import { useEffect, useState } from "react";
import type { DateRange } from "../state/timeRange";
import { getUsage } from "../api";
import type { Series, SeriesPoint } from "../api";
import { makeAllSeries } from "../state/metricsMock";

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

/** Simple moving average — keeps the same number of points, uses available window at edges. */
function smoothPoints(points: SeriesPoint[], window: number = 7): SeriesPoint[] {
  return points.map((p, i) => {
    const start = Math.max(0, i - window + 1);
    const chunk = points.slice(start, i + 1);
    const avg = chunk.reduce((sum, pt) => sum + pt.value, 0) / chunk.length;
    return { date: p.date, value: Math.round(avg * 10) / 10 };
  });
}

function smoothSeries(series: Series[], window: number = 7): Series[] {
  return series.map((s) => ({ ...s, points: smoothPoints(s.points, window) }));
}

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

        const fetched = res?.series ?? [];
        // Keep placeholder series (empty points) if API returned nothing — polling will fill them in
        setSeries(fetched.length > 0 ? smoothSeries(fetched) : PLACEHOLDER_SERIES);
        setStatus("success");
      } catch (e) {
        if (cancelled) return;

        console.error(e);

        if (IS_MOCK) {
          setSeries(smoothSeries(makeAllSeries(range)));
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
  }, [range.start, range.end, range.preset]);

  return { status, error, series, isMock: IS_MOCK };
}

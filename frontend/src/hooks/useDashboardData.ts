import { useEffect, useState } from "react";
import type { DateRange } from "../state/timeRange";
import { getUsage } from "../api";
import type { Series, SeriesPoint } from "../api";
import { makeAllSeries } from "../state/metricsMock";

type Status = "idle" | "loading" | "success" | "error";

const IS_MOCK = import.meta.env.VITE_USE_MOCKS === "true";

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
  const [series, setSeries] = useState<Series[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setStatus("loading");
      setError(null);

      try {
        const res = await getUsage({ start: range.start, end: range.end });
        if (cancelled) return;

        setSeries(smoothSeries(res?.series ?? []));
        setStatus("success");
      } catch (e) {
        if (cancelled) return;

        console.error(e);

        if (IS_MOCK) {
          setSeries(smoothSeries(makeAllSeries(range)));
          setStatus("success");
          return;
        }

        setSeries([]);
        setStatus("error");
        setError("Failed to load dashboard metrics.");
      }
    }

    run();

    return () => { cancelled = true; };
  }, [range.start, range.end, range.preset]);

  return { status, error, series, isMock: IS_MOCK };
}

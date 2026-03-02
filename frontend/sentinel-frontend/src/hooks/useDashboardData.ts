// src/hooks/useDashboardData.ts
import { useEffect, useMemo, useState } from "react";
import type { DateRange } from "../state/timeRange";
import { makeAllSeries } from "../state/metricsMock";
import { getUsage } from "../api";
import type { Series } from "../api";

type Status = "idle" | "loading" | "success" | "error";

export function useDashboardData(range: DateRange) {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  const mockSeries = useMemo(() => makeAllSeries(range), [range]);

  const [series, setSeries] = useState<Series[]>(mockSeries);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setStatus("loading");
      setError(null);

      try {
        const res = await getUsage({ start: range.start, end: range.end });
        if (cancelled) return;

        setSeries(res.series);
        setStatus("success");
      } catch {
        if (cancelled) return;

        setSeries(mockSeries);
        setStatus("error");
        setError("Backend unavailable – showing mock data.");
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, [range.start, range.end, mockSeries]);

  return { status, error, series, isMock: status === "error" };
}
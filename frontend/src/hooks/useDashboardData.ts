// src/hooks/useDashboardData.ts
import { useEffect, useState } from "react";
import type { DateRange } from "../state/timeRange";
import { getUsage } from "../api";
import type { Series } from "../api";
import { makeAllSeries } from "../state/metricsMock";

type Status = "idle" | "loading" | "success" | "error";

const IS_MOCK = import.meta.env.VITE_USE_MOCKS === "true";

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

        setSeries(res?.series ?? []);
        setStatus("success");
      } catch (e) {
        if (cancelled) return;

        console.error(e);

        if (IS_MOCK) {
          setSeries(makeAllSeries(range));
          setStatus("success");
          return;
        }

        setSeries([]);
        setStatus("error");
        setError("Failed to load dashboard metrics.");
      }
    }

    run();

    return () => {
      cancelled = true;
    };
  }, [range.start, range.end, range.preset]);

  return { status, error, series, isMock: IS_MOCK };
}
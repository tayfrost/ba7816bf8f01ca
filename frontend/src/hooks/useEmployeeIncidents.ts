import { useEffect, useState } from "react";
import { getEmployeeIncidents } from "../api";
import type { Incident, Series } from "../api";
import { enumerateDays } from "../state/timeRange";
import type { DateRange } from "../state/timeRange";

type Status = "idle" | "loading" | "success" | "error";

const CATEGORIES = [
  { key: "depression",        label: "Depression" },
  { key: "burnout",           label: "Burnout" },
  { key: "stress",            label: "Stress" },
  { key: "harassment",        label: "Harassment" },
  { key: "suicidal_ideation", label: "Suicidal ideation" },
];

const PLACEHOLDER_SERIES: Series[] = CATEGORIES.map(({ key, label }) => ({
  key,
  label,
  points: [],
}));

/**
 * Log-damped count: 1 incident → 3.2, 5 → 7.2, 10 → 10 (capped).
 * Normalised so count=10 maps to exactly 10.
 */
const LOG_NORM = 10 / Math.log2(11);
function logDampedCount(count: number): number {
  return Math.min(10, Math.log2(1 + count) * LOG_NORM);
}

/** Build a per-category time series from raw incidents over the given date range. */
function buildCategorySeries(incidents: Incident[], start: string, end: string): Series[] {
  const allDates = enumerateDays(start, end);

  return CATEGORIES.map(({ key, label }) => {
    const daily: Record<string, number> = {};
    allDates.forEach((d) => { daily[d] = 0; });

    incidents.forEach((inc) => {
      if (inc.class_reason !== key) return;
      const date = (inc.created_at || inc.message_ts || "").slice(0, 10);
      if (date in daily) daily[date]++;
    });

    return {
      key,
      label,
      points: allDates.map((date) => ({
        date,
        value: logDampedCount(daily[date]),
      })),
    };
  });
}

export function useEmployeeIncidents(userId: string, range?: DateRange) {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [series, setSeries] = useState<Series[]>(PLACEHOLDER_SERIES);

  // Default to last 30 days when no range is provided
  const start = range?.start ?? (() => {
    const d = new Date();
    d.setDate(d.getDate() - 29);
    return d.toISOString().slice(0, 10);
  })();
  const end = range?.end ?? new Date().toISOString().slice(0, 10);

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;

    async function load() {
      setStatus("loading");
      setError(null);
      try {
        const data = await getEmployeeIncidents(userId, 500, start, end);
        if (cancelled) return;
        setIncidents(data);
        setSeries(buildCategorySeries(data, start, end));
        setStatus("success");
      } catch (err) {
        if (cancelled) return;
        console.error(err);
        setStatus("error");
        setError("Failed to load employee incidents.");
      }
    }

    load();
    const interval = setInterval(load, 30_000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [userId, start, end]);

  return { status, error, incidents, series };
}

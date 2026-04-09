import { useEffect, useState } from "react";
import { getEmployeeIncidents } from "../api";
import type { Incident, Series } from "../api";
import { enumerateDays } from "../state/timeRange";

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

function toYMD(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/** Build a 30-day per-category time series from raw incidents. */
function buildCategorySeries(incidents: Incident[]): Series[] {
  const today = new Date();
  const start = new Date(today);
  start.setDate(today.getDate() - 29);
  const allDates = enumerateDays(toYMD(start), toYMD(today));

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
      points: allDates.map((date) => ({ date, value: daily[date] })),
    };
  });
}

export function useEmployeeIncidents(userId: string) {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [series, setSeries] = useState<Series[]>(PLACEHOLDER_SERIES);

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;

    async function load() {
      setStatus("loading");
      setError(null);
      try {
        const data = await getEmployeeIncidents(userId);
        if (cancelled) return;
        setIncidents(data);
        setSeries(buildCategorySeries(data));
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
  }, [userId]);

  return { status, error, incidents, series };
}

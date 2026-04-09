import { useEffect, useState } from "react";
import { getEmployeeIncidents } from "../api";
import type { Incident, Series } from "../api";
import { enumerateDays } from "../state/timeRange";
import type { DateRange } from "../state/timeRange";
import { dashboardDebug, dashboardDebugError, summarizeSeries } from "../utils/dashboardDebug";

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

  dashboardDebug("useEmployeeIncidents", "build-series-start", {
    incidentsCount: incidents.length,
    start,
    end,
    days: allDates.length,
  });

  const result = CATEGORIES.map(({ key, label }) => {
    const daily: Record<string, number> = {};
    allDates.forEach((d) => { daily[d] = 0; });

    incidents.forEach((inc) => {
      if (inc.class_reason !== key) return;
      const date = (inc.created_at || inc.message_ts || "").slice(0, 10);
      if (date in daily) daily[date]++;
    });

    const points = allDates.map((date) => ({
      date,
      value: logDampedCount(daily[date]),
    }));

    dashboardDebug("useEmployeeIncidents", "category-built", {
      key,
      label,
      rawDailyMax: Math.max(...allDates.map((d) => daily[d])),
      rawDailyTotal: allDates.reduce((sum, d) => sum + daily[d], 0),
      pointsPreview: {
        first: points[0] ?? null,
        last: points[points.length - 1] ?? null,
      },
    });

    return {
      key,
      label,
      points,
    };
  });

  dashboardDebug("useEmployeeIncidents", "build-series-complete", {
    summary: summarizeSeries(result, 10),
  });

  return result;
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

    dashboardDebug("useEmployeeIncidents", "effect-start", {
      userId,
      start,
      end,
      pollIntervalMs: 30000,
    });

    async function load() {
      setStatus("loading");
      setError(null);
      dashboardDebug("useEmployeeIncidents", "fetch-start", {
        userId,
        start,
        end,
        limit: 500,
      });
      try {
        const data = await getEmployeeIncidents(userId, 500, start, end);
        if (cancelled) return;
        dashboardDebug("useEmployeeIncidents", "fetch-success", {
          userId,
          incidentCount: data.length,
          reasonBreakdown: data.reduce<Record<string, number>>((acc, inc) => {
            const key = inc.class_reason || "unknown";
            acc[key] = (acc[key] || 0) + 1;
            return acc;
          }, {}),
          firstIncidentDate: data[0]?.created_at ?? null,
          lastIncidentDate: data[data.length - 1]?.created_at ?? null,
        });
        setIncidents(data);
        const nextSeries = buildCategorySeries(data, start, end);
        setSeries(nextSeries);
        setStatus("success");
        dashboardDebug("useEmployeeIncidents", "state-success", {
          userId,
          seriesSummary: summarizeSeries(nextSeries, 10),
        });
      } catch (err) {
        if (cancelled) return;
        console.error(err);
        dashboardDebugError("useEmployeeIncidents", "fetch-failed", err, {
          userId,
          start,
          end,
        });
        setStatus("error");
        setError("Failed to load employee incidents.");
        dashboardDebug("useEmployeeIncidents", "state-error", {
          userId,
          error: "Failed to load employee incidents.",
        });
      }
    }

    load();
    const interval = setInterval(load, 30_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
      dashboardDebug("useEmployeeIncidents", "effect-cleanup", { userId, start, end });
    };
  }, [userId, start, end]);

  return { status, error, incidents, series };
}

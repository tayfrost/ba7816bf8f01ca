type PointLike = { date: string; value: number };
type SeriesLike = { key: string; label?: string; points: PointLike[] };

const DASHBOARD_DEBUG = import.meta.env.VITE_DASHBOARD_DEBUG === "true";

function nowIso() {
  return new Date().toISOString();
}

function summarizePoints(points: PointLike[], scale?: number) {
  if (!points || points.length === 0) {
    return {
      points: 0,
      dateStart: null,
      dateEnd: null,
      min: null,
      max: null,
      latest: null,
      nonZeroCount: 0,
      aboveScaleCount: 0,
    };
  }

  const values = points.map((p) => p.value);
  const nonZeroCount = values.filter((v) => v !== 0).length;
  const aboveScaleCount = typeof scale === "number"
    ? values.filter((v) => v > scale).length
    : 0;

  return {
    points: points.length,
    dateStart: points[0]?.date ?? null,
    dateEnd: points[points.length - 1]?.date ?? null,
    min: Math.min(...values),
    max: Math.max(...values),
    latest: values[values.length - 1],
    nonZeroCount,
    aboveScaleCount,
  };
}

export function summarizeSeries(series: SeriesLike[], scale?: number) {
  return (series || []).map((s) => ({
    key: s.key,
    label: s.label ?? s.key,
    ...summarizePoints(s.points || [], scale),
  }));
}

export function dashboardDebug(scope: string, message: string, payload?: unknown) {
  if (!DASHBOARD_DEBUG) return;
  const prefix = `[dashboard-debug][${nowIso()}][${scope}] ${message}`;
  if (typeof payload === "undefined") {
    console.log(prefix);
    return;
  }
  console.log(prefix, payload);
}

export function dashboardDebugError(scope: string, message: string, error: unknown, payload?: unknown) {
  if (!DASHBOARD_DEBUG) return;
  const prefix = `[dashboard-debug][${nowIso()}][${scope}] ${message}`;
  if (typeof payload === "undefined") {
    console.error(prefix, error);
    return;
  }
  console.error(prefix, error, payload);
}

export function isDashboardDebugEnabled() {
  return DASHBOARD_DEBUG;
}

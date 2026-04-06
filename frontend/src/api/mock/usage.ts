import type { UsageQuery, UsageResponse } from "../usage";
import { makeAllSeries } from "../../state/metricsMock";

export async function getUsage(q: UsageQuery): Promise<UsageResponse> {
  const range = { start: q.start, end: q.end };
  const series = makeAllSeries(range);

  const filtered =
    q.metrics && q.metrics.length > 0
      ? series.filter((s) => q.metrics!.includes(s.key))
      : series;

  return { range, series: filtered };
}
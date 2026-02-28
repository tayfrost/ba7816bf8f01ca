export type RangePreset = "week" | "month" | "year" | "all" | "custom";

export type DateRange = {
  preset: RangePreset;
  start: string; // YYYY-MM-DD
  end: string;   // YYYY-MM-DD
};

function toYMD(d: Date) {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

export function computeRange(preset: RangePreset, custom?: { start: string; end: string }): DateRange {
  const today = new Date();
  const end = toYMD(today);

  if (preset === "custom" && custom) return { preset, start: custom.start, end: custom.end };
  if (preset === "all") return { preset, start: "2020-01-01", end }; // placeholder

  const startDate = new Date(today);
  if (preset === "week") startDate.setDate(today.getDate() - 6);
  if (preset === "month") startDate.setMonth(today.getMonth() - 1);
  if (preset === "year") startDate.setFullYear(today.getFullYear() - 1);

  return { preset, start: toYMD(startDate), end };
}

export function enumerateDays(startYMD: string, endYMD: string): string[] {
  const out: string[] = [];
  const start = new Date(`${startYMD}T00:00:00`);
  const end = new Date(`${endYMD}T00:00:00`);
  const cur = new Date(start);

  while (cur <= end) {
    out.push(toYMD(cur));
    cur.setDate(cur.getDate() + 1);
  }
  return out;
}
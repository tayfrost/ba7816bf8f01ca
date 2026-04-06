import type { RangePreset } from "../../state/timeRange";

type Props = {
  preset: RangePreset;
  setPreset: (preset: RangePreset) => void;
};

const BRAND_ORANGE = "var(--color-top)";

export default function RangeSelector({ preset, setPreset }: Props) {
  return (
    <div
      style={{
        display: "flex",
        gap: "8px",
        background: "rgba(0,0,0,0.5)",
        padding: "6px",
        borderRadius: "50px",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      {["week", "month", "year", "all", "custom"].map((p) => (
        <button
          key={p}
          onClick={() => setPreset(p as RangePreset)}
          style={{
            padding: "10px 22px",
            borderRadius: "40px",
            border: "none",
            cursor: "pointer",
            fontWeight: "900",
            fontSize: "11px",
            textTransform: "uppercase",
            background: preset === p ? BRAND_ORANGE : "transparent",
            color: preset === p ? "#1a011d" : "rgba(255,255,255,0.5)",
            transition: "all 0.3s ease",
            boxShadow:
              preset === p ? "0 0 20px rgba(227, 141, 38, 0.5)" : "none",
          }}
        >
          {p}
        </button>
      ))}
    </div>
  );
}
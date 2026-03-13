import type { Series } from "../../api";

type Props = {
  series: Series[];
  activeIndex: number;
  setActiveIndex: (i: number) => void;
};

const BRAND_ORANGE = "var(--color-top)";

export default function MetricTabs({
  series,
  activeIndex,
  setActiveIndex,
}: Props) {
  return (
    <div
      style={{
        display: "flex",
        gap: "12px",
        marginBottom: "40px",
        flexWrap: "wrap",
        justifyContent: "center",
      }}
    >
      {series.map((s, idx) => (
        <button
          key={s.key}
          onClick={() => setActiveIndex(idx)}
          style={{
            padding: "10px 20px",
            borderRadius: "15px",
            border:
              activeIndex === idx
                ? `1px solid ${BRAND_ORANGE}`
                : "1px solid rgba(255,255,255,0.1)",
            background:
              activeIndex === idx
                ? `rgba(227, 141, 38, 0.2)`
                : "rgba(255,255,255,0.02)",
            color:
              activeIndex === idx
                ? BRAND_ORANGE
                : "rgba(255,255,255,0.5)",
            fontWeight: "800",
            cursor: "pointer",
            fontSize: "12px",
            transition: "all 0.2s",
          }}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
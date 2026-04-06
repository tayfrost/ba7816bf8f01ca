import type { Series } from "../../api";
import SimpleLineChart from "../SimpleLineChart";

type Props = {
  series: Series[];
  activeIndex: number;
  setActiveIndex: (i: number) => void;
};

export default function MetricCarousel({
  series,
  activeIndex,
  setActiveIndex,
}: Props) {
  return (
    <div
      style={{
        display: "flex",
        gap: "20px",
        overflowX: "auto",
        paddingBottom: "20px",
        marginTop: "20px",
      }}
    >
      {series
        .filter((_, i) => i !== activeIndex)
        .map((s) => (
          <div
            key={s.key}
            style={{
              minWidth: "300px",
              background: "rgba(255, 255, 255, 0.02)",
              border: "1px solid rgba(255, 255, 255, 0.05)",
              borderRadius: "24px",
              padding: "20px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              cursor: "pointer",
            }}
            onClick={() => setActiveIndex(series.indexOf(s))}
          >
            <h4
              style={{
                fontSize: "12px",
                fontWeight: "900",
                margin: "0 0 15px 0",
                color: "rgba(255,255,255,0.6)",
              }}
            >
              {s.label}
            </h4>

            <SimpleLineChart points={s.points} width={260} height={100} />
          </div>
        ))}
    </div>
  );
}
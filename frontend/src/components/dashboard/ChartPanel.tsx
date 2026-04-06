import type { Series } from "../../api";
import SimpleLineChart from "../SimpleLineChart";
import MetricTabs from "./MetricTabs";

type Props = {
  series: Series[];
  activeIndex: number;
  setActiveIndex: (i: number) => void;
};

export default function ChartPanel({
  series,
  activeIndex,
  setActiveIndex,
}: Props) {
  return (
    <div
      style={{
        background: "rgba(255, 255, 255, 0.03)",
        padding: "50px",
        borderRadius: "50px",
        border: "1px solid rgba(255,255,255,0.1)",
        boxShadow: "0 20px 50px rgba(0,0,0,0.3)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <MetricTabs
        series={series}
        activeIndex={activeIndex}
        setActiveIndex={setActiveIndex}
      />

      <SimpleLineChart
        points={series[activeIndex]?.points || []}
        width={850}
        height={400}
      />
    </div>
  );
}
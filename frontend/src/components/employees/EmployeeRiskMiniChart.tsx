import SimpleLineChart from "../SimpleLineChart";

type Point = {
  date: string;
  value: number;
};

type Props = {
  points: Point[];
};

export default function EmployeeRiskMiniChart({ points }: Props) {
  return (
    <div style={{ marginTop: "18px" }}>
      <div
        style={{
          fontSize: "10px",
          fontWeight: 900,
          letterSpacing: "1px",
          textTransform: "uppercase",
          opacity: 0.45,
          marginBottom: "10px",
        }}
      >
        Risk trend
      </div>

      <SimpleLineChart points={points} width={260} height={100} />
    </div>
  );
}
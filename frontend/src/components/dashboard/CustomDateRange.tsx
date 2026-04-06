type Props = {
  customStart: string;
  customEnd: string;
  setCustomStart: (value: string) => void;
  setCustomEnd: (value: string) => void;
};

const BRAND_ORANGE = "var(--color-top)";

export default function CustomDateRange({
  customStart,
  customEnd,
  setCustomStart,
  setCustomEnd,
}: Props) {
  return (
    <div
      style={{
        marginBottom: "30px",
        display: "flex",
        gap: "20px",
        background: "rgba(255,255,255,0.04)",
        padding: "15px 25px",
        borderRadius: "20px",
        border: "1px solid rgba(255,255,255,0.1)",
        width: "fit-content",
      }}
    >
      <label
        style={{
          fontSize: "11px",
          fontWeight: "900",
          color: BRAND_ORANGE,
        }}
      >
        START{" "}
        <input
          type="date"
          value={customStart}
          onChange={(e) => setCustomStart(e.target.value)}
          style={{
            background: "transparent",
            color: "#fff",
            border: "none",
            marginLeft: "10px",
            fontWeight: "bold",
            outline: "none",
          }}
        />
      </label>

      <label
        style={{
          fontSize: "11px",
          fontWeight: "900",
          color: BRAND_ORANGE,
        }}
      >
        END{" "}
        <input
          type="date"
          value={customEnd}
          onChange={(e) => setCustomEnd(e.target.value)}
          style={{
            background: "transparent",
            color: "#fff",
            border: "none",
            marginLeft: "10px",
            fontWeight: "bold",
            outline: "none",
          }}
        />
      </label>
    </div>
  );
}
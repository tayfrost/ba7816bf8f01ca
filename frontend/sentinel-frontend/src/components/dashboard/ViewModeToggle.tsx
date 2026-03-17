type Props = {
  viewMode: "focused" | "grid";
  setViewMode: (mode: "focused" | "grid") => void;
};

const BRAND_ORANGE = "var(--color-top)";

export default function ViewModeToggle({ viewMode, setViewMode }: Props) {
  return (
    <div style={{ display: "flex", gap: "25px" }}>
      <button
        onClick={() => setViewMode("focused")}
        style={{
          background: "none",
          border: "none",
          color: viewMode === "focused" ? BRAND_ORANGE : "rgba(255,255,255,0.3)",
          fontWeight: "900",
          cursor: "pointer",
          fontSize: "12px",
          letterSpacing: "1px",
        }}
      >
        FOCUS
      </button>

      <button
        onClick={() => setViewMode("grid")}
        style={{
          background: "none",
          border: "none",
          color: viewMode === "grid" ? BRAND_ORANGE : "rgba(255,255,255,0.3)",
          fontWeight: "900",
          cursor: "pointer",
          fontSize: "12px",
          letterSpacing: "1px",
        }}
      >
        GRID
      </button>
    </div>
  );
}
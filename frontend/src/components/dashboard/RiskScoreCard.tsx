type Props = {
  riskScore: number;
};

const BRAND_ORANGE = "var(--color-top)";
const BRAND_DEEP = "var(--color-brand-deep)";

export default function RiskScoreCard({ riskScore }: Props) {
  return (
    <div
      style={{
        width: "140px",
        height: "140px",
        background: `linear-gradient(135deg, rgba(227, 141, 38, 0.3) 0%, ${BRAND_DEEP} 100%)`,
        border: `2px solid ${BRAND_ORANGE}`,
        borderRadius: "32px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        boxShadow: `0 0 40px rgba(227, 141, 38, 0.2)`,
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: -20,
          left: -20,
          width: 70,
          height: 70,
          background: BRAND_ORANGE,
          filter: "blur(45px)",
          opacity: 0.4,
        }}
      />
      <span
        style={{
          fontSize: "12px",
          fontWeight: "900",
          color: BRAND_ORANGE,
          letterSpacing: "2px",
          marginBottom: "4px",
          zIndex: 1,
        }}
      >
        RISK
      </span>
      <span
        style={{
          fontSize: "48px",
          fontWeight: "900",
          color: "#fff",
          zIndex: 1,
        }}
      >
        {riskScore}%
      </span>
    </div>
  );
}
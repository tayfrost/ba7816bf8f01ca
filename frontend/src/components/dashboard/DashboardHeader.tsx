import RiskScoreCard from "./RiskScoreCard";

type Props = {
  companyName?: string;
  plan?: string | null;
  connectedCount: number;
  riskScore: number;
};

const BRAND_ORANGE = "var(--color-top)";

export default function DashboardHeader({
  companyName,
  plan,
  connectedCount,
  riskScore,
}: Props) {
  return (
    <header
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "50px",
      }}
    >
      <div>
        <h1
          style={{
            fontSize: "38px",
            fontWeight: "900",
            margin: 0,
            letterSpacing: "-1px",
          }}
        >
          Welcome,{" "}
          <span
            style={{
              color: BRAND_ORANGE,
              textShadow: "0 0 20px rgba(227, 141, 38, 0.3)",
            }}
          >
            {companyName}
          </span>
        </h1>

        <p
          style={{
            opacity: 0.5,
            marginTop: "10px",
            fontWeight: "700",
            textTransform: "uppercase",
            fontSize: "12px",
            letterSpacing: "1px",
          }}
        >
          {plan} MEMBER • {connectedCount} ACTIVE SOURCES
        </p>
      </div>

      <RiskScoreCard riskScore={riskScore} />
    </header>
  );
}
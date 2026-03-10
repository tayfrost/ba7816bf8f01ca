type Props = {
  status: "idle" | "loading" | "success" | "error";
  error?: string | null;
  isMock?: boolean;
};

const BRAND_ORANGE = "var(--color-top)";

export default function StatusBanner({ status, error, isMock }: Props) {
  if (status === "loading") {
    return (
      <div style={{ marginBottom: 18, opacity: 0.8 }}>
        Loading metrics…
      </div>
    );
  }

  if (status === "error" && error) {
    return (
      <div
        style={{
          marginBottom: 18,
          opacity: 0.9,
          color: BRAND_ORANGE,
          fontWeight: 800,
        }}
      >
        {error}
      </div>
    );
  }

  if (isMock) {
    return (
      <div
        style={{
          marginBottom: 18,
          opacity: 0.9,
          color: BRAND_ORANGE,
          fontWeight: 800,
        }}
      >
        Showing mock data (mock mode enabled)
      </div>
    );
  }

  return null;
}
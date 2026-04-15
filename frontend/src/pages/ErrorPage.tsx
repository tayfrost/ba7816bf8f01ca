import { useNavigate, useSearchParams } from "react-router-dom";

type Props = {
  code?: number | string;
  message?: string;
};

export default function ErrorPage({ code: codeProp, message: messageProp }: Props) {
  const navigate = useNavigate();
  const [params] = useSearchParams();

  // Props take precedence; fall back to query string (used when navigated to via URL)
  const code    = codeProp    ?? params.get("code")    ?? undefined;
  const message = messageProp ?? params.get("message") ?? undefined;

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(to bottom, #20022bfd, #1a011d)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'Outfit', 'Inter', sans-serif",
        color: "#fff",
        padding: "40px 20px",
        textAlign: "center",
      }}
    >
      {/* Logo */}
      <img
        src="/logo-icon.png"
        alt="SentinelAI"
        style={{ height: "64px", marginBottom: "40px", opacity: 0.6 }}
      />

      {/* Error code */}
      {code && (
        <div
          style={{
            fontSize: "80px",
            fontWeight: 900,
            letterSpacing: "-4px",
            color: "var(--color-top, #e38d26)",
            lineHeight: 1,
            marginBottom: "16px",
            textShadow: "0 0 60px rgba(227,141,38,0.3)",
          }}
        >
          {code}
        </div>
      )}

      {/* Heading */}
      <h1
        style={{
          fontSize: "28px",
          fontWeight: 900,
          margin: "0 0 12px",
          letterSpacing: "-0.5px",
        }}
      >
        Something went wrong
      </h1>

      {/* Message */}
      <p
        style={{
          fontSize: "14px",
          opacity: 0.5,
          maxWidth: "400px",
          lineHeight: 1.6,
          margin: "0 0 40px",
        }}
      >
        {message || "An unexpected error occurred. Please try again or return to the home page."}
      </p>

      {/* CTA */}
      <button
        onClick={() => navigate("/plan")}
        style={{
          background: "var(--color-top, #e38d26)",
          color: "#fff",
          border: "none",
          borderRadius: "14px",
          padding: "14px 36px",
          fontSize: "14px",
          fontWeight: 900,
          letterSpacing: "1px",
          cursor: "pointer",
          boxShadow: "0 0 30px rgba(227,141,38,0.3)",
          transition: "opacity 0.2s",
        }}
        onMouseOver={(e) => (e.currentTarget.style.opacity = "0.8")}
        onMouseOut={(e) => (e.currentTarget.style.opacity = "1")}
      >
        BACK TO HOME
      </button>
    </div>
  );
}

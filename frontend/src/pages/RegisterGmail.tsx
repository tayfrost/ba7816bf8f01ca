import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import Button from "../components/Button";
import LandingHeader from "../components/LandingHeader";

/**
 * Public self-service Gmail registration page for individual team members.
 *
 * No SentinelAI account required. The admin shares the link:
 *   https://sentinelai.work/register-gmail?company_id=<id>
 *
 * The employee clicks it, connects their Gmail via OAuth, and their mailbox
 * is added to the company's monitoring — nothing else needed.
 */
export default function RegisterGmail() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const companyId = searchParams.get("company_id");

  const [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Handle redirect back from Google OAuth via gmail_controller callback
  useEffect(() => {
    const provider = searchParams.get("provider");
    const oauthStatus = searchParams.get("status");

    if (provider === "gmail" && oauthStatus === "success") {
      setConnected(true);
      setNotice("Gmail connected successfully. SentinelAI will now monitor your mailbox.");
      // Keep company_id in URL, strip only the OAuth params
      setSearchParams(companyId ? { company_id: companyId } : {}, { replace: true });
    }

    if (provider === "gmail" && oauthStatus === "email_conflict") {
      setError(
        "This Gmail address is already connected to another SentinelAI workspace. Please contact your admin."
      );
      setSearchParams(companyId ? { company_id: companyId } : {}, { replace: true });
    }

    if (provider === "gmail" && oauthStatus === "error") {
      setError(
        "Gmail connection failed. The link may have expired or your company's seat limit has been reached. Contact your admin."
      );
      setSearchParams(companyId ? { company_id: companyId } : {}, { replace: true });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleConnect() {
    if (!companyId) {
      setError("Invalid link — company ID is missing. Ask your admin to reshare the link.");
      return;
    }
    setBusy(true);
    // Redirect directly to the Gmail OAuth login — no API call needed.
    // The backend encodes company_id + return_page into the OAuth state.
    window.location.href = `/gmail/oauth/login?company_id=${companyId}&return_page=register-gmail`;
  }

  // Missing company_id — the link is broken
  if (!companyId && !connected) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          background: "linear-gradient(to bottom, #20022bfd, #1a011d)",
          color: "white",
          fontFamily: "'Outfit', 'Inter', sans-serif",
          textAlign: "center",
          padding: "2rem",
        }}
      >
        <div>
          <p style={{ fontSize: "3rem", marginBottom: "1rem" }}>🔗</p>
          <h2 style={{ fontSize: "1.75rem", fontWeight: 900, marginBottom: "0.75rem" }}>
            Invalid Link
          </h2>
          <p style={{ opacity: 0.65, maxWidth: "340px", lineHeight: 1.6 }}>
            This link is missing a company ID. Ask your admin to reshare the correct link from their Settings page.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col font-sans">
      <LandingHeader isLoggedIn={false} />

      <main className="flex-grow flex items-center justify-center pt-24 pb-12 px-6">
        <div
          style={{ background: "var(--dynamic-card)" }}
          className="max-w-2xl w-full backdrop-blur-3xl border border-white/30 shadow-xl rounded-[32px] md:rounded-[48px] p-6 md:p-14"
        >
          {/* Header */}
          <div className="mb-10">
            <h1
              style={{ color: "var(--dynamic-text)" }}
              className="text-3xl md:text-4xl font-serif font-black mb-3"
            >
              Register your Gmail
            </h1>
            <p
              style={{ color: "var(--dynamic-text)", opacity: 0.8 }}
              className="text-base font-medium leading-relaxed"
            >
              Your company has invited you to connect your work Gmail to SentinelAI.
              This allows early wellbeing signals to be detected as part of a
              consent-based, company-approved analysis. You only need to do this once.
            </p>
          </div>

          {/* Status banners */}
          {notice && (
            <div className="mb-6 px-5 py-4 rounded-2xl bg-green-100/20 border border-green-400/30 text-sm font-semibold text-green-400">
              {notice}
            </div>
          )}
          {error && (
            <div className="mb-6 px-5 py-4 rounded-2xl bg-red-100/20 border border-red-400/30 text-sm font-semibold text-red-400">
              {error}
            </div>
          )}

          {/* Gmail card */}
          <div
            style={{
              background: "var(--dynamic-card)",
              borderColor: "var(--dynamic-border)",
            }}
            className="group relative flex flex-col md:flex-row items-center justify-between p-6 md:p-8 rounded-[28px] border shadow-sm transition-all duration-500 hover:shadow-xl hover:-translate-y-1 mb-10"
          >
            <div className="flex flex-col md:flex-row items-center gap-6 text-center md:text-left">
              <div className="w-14 h-14 flex items-center justify-center p-3 rounded-2xl bg-white/50 border border-white transition-transform group-hover:scale-105">
                <img
                  src="/logos/gmail.svg"
                  alt="Gmail"
                  className="w-full h-full object-contain"
                />
              </div>

              <div>
                <div className="flex items-center justify-center md:justify-start gap-3 mb-1">
                  <h3
                    style={{ color: "var(--dynamic-text)" }}
                    className="text-xl font-bold tracking-tight"
                  >
                    Gmail
                  </h3>
                  {connected && (
                    <span className="text-[9px] font-black uppercase tracking-widest text-green-700 bg-green-100/80 px-2 py-0.5 rounded-md">
                      Connected
                    </span>
                  )}
                </div>
                <p
                  style={{ color: "var(--dynamic-text)" }}
                  className="text-[15px] opacity-80 font-medium leading-relaxed max-w-sm"
                >
                  Connect your mailbox for consent-based behavioural wellbeing signals.
                  Only metadata is analysed — message content stays private.
                </p>
              </div>
            </div>

            <div className="mt-6 md:mt-0 shrink-0">
              {connected ? (
                <Button
                  variant="secondary"
                  className="min-w-[120px] px-6 py-2.5 text-xs font-bold"
                  disabled
                >
                  Connected ✓
                </Button>
              ) : (
                <Button
                  onClick={handleConnect}
                  variant="primary"
                  className="min-w-[120px] px-6 py-2.5 text-xs font-bold"
                  disabled={busy}
                >
                  {busy ? "Redirecting..." : "Connect Gmail"}
                </Button>
              )}
            </div>
          </div>

          {/* Footer bar */}
          <div
            style={{
              background: "var(--dynamic-card)",
              borderColor: "var(--dynamic-border)",
            }}
            className="rounded-[28px] py-5 px-8 flex flex-col sm:flex-row items-center justify-between gap-4 border backdrop-blur-sm"
          >
            <div className="flex items-center gap-3">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse shrink-0" />
              <p
                style={{ color: "var(--dynamic-text)" }}
                className="text-[10px] font-bold uppercase tracking-widest opacity-60 leading-relaxed"
              >
                Consent-based monitoring only. HR decisions remain human-in-the-loop.
              </p>
            </div>

            {connected && (
              <Button
                onClick={() => navigate("/")}
                variant="secondary"
                className="whitespace-nowrap px-6 py-2.5 text-xs font-bold"
              >
                Done
              </Button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

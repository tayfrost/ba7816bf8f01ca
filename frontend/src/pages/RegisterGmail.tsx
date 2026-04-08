import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import Button from "../components/Button";
import LandingHeader from "../components/LandingHeader";
import { startMemberGmail } from "../api";

/**
 * Self-service Gmail registration page for individual team members.
 *
 * Unlike /connect-accounts (which is for admins wiring up the whole workspace),
 * this page lets a single employee add their own Gmail so SentinelAI can monitor
 * their mailbox as part of the company's consent-based analysis.
 *
 * Access: requires a valid JWT token (RequireAuth) + paid plan (RequirePaidPlan).
 * Share the link https://sentinelai.work/register-gmail in your team Slack channel.
 */
export default function RegisterGmail() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Handle OAuth redirect back from Google via the gmail_controller callback
  useEffect(() => {
    const provider = searchParams.get("provider");
    const oauthStatus = searchParams.get("status");

    if (provider === "gmail" && oauthStatus === "success") {
      setConnected(true);
      setNotice("Gmail connected successfully. SentinelAI will now monitor your mailbox.");
      setSearchParams({}, { replace: true });
    }

    if (provider === "gmail" && oauthStatus === "error") {
      setError("Gmail connection failed. Please try again or contact your admin.");
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  async function handleConnect() {
    setBusy(true);
    setError(null);
    setNotice(null);

    try {
      const { url } = await startMemberGmail();
      window.location.href = url;
    } catch (err) {
      console.error("[register-gmail] start failed:", err);
      setError("Failed to start Gmail connection. Please try again.");
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col font-sans">
      <LandingHeader isLoggedIn={true} />

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
              Connect your work Gmail so SentinelAI can monitor early wellbeing
              signals as part of your company's consent-based analysis. Your
              admin shared this link — you only need to do this once.
            </p>
          </div>

          {/* Status banners */}
          {notice && (
            <div className="mb-6 px-5 py-3 rounded-2xl bg-green-100/20 border border-green-400/30 text-sm font-semibold text-green-400">
              {notice}
            </div>
          )}
          {error && (
            <div className="mb-6 px-5 py-3 rounded-2xl bg-red-100/20 border border-red-400/30 text-sm font-semibold text-red-400">
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
                  Connect your mailbox metadata (consent-based) for behavioural
                  wellbeing signals. Only metadata is analysed — message content
                  stays private.
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
                  Connected
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

            <Button
              onClick={() => navigate("/dashboard")}
              variant="secondary"
              className="whitespace-nowrap px-6 py-2.5 text-xs font-bold opacity-70 hover:opacity-100 transition-all"
            >
              {connected ? "Go to Dashboard" : "Skip for now"}
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}

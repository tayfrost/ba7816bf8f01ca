import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import Button from "../components/Button";
import LandingHeader from "../components/LandingHeader";
import { useOnboarding } from "../state/onboarding";
import { getIntegrations, startIntegration, disconnectIntegration } from "../api";

type Provider = "slack" | "gmail" | "outlook";

function providerTitle(p: Provider) {
  if (p === "slack") return "Slack";
  if (p === "gmail") return "Gmail";
  return "Outlook";
}

function providerLogo(p: Provider) {
  return `/logos/${p}.svg`;
}

function providerDesc(p: Provider) {
  if (p === "slack") return "Connect a workspace to ingest messages via approved channels.";
  if (p === "gmail") return "Connect mailbox metadata (consent-based) for behavioural signals.";
  return "Connect Outlook to ingest organisational communication signals.";
}

export default function ConnectAccounts() {
  const nav = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const { integrations, setIntegrationConnected } = useOnboarding();
  const providers = useMemo<Provider[]>(() => ["slack", "gmail", "outlook"], []);

  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [busyProvider, setBusyProvider] = useState<Provider | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refreshIntegrations = useCallback(async () => {
    setStatus("loading");
    setError(null);

    try {
      const apiIntegrations = await getIntegrations();

      apiIntegrations.forEach((integration) => {
        setIntegrationConnected(integration.provider, integration.connected);
      });

      setStatus("success");
    } catch (err) {
      console.error(err);
      setStatus("error");
      setError("Failed to load integrations.");
    }
  }, [setIntegrationConnected]);

  useEffect(() => {
    refreshIntegrations();
  }, [refreshIntegrations]);

  useEffect(() => {
    const provider = searchParams.get("provider");
    const oauthStatus = searchParams.get("status");

    if (provider && oauthStatus === "success") {
      setNotice(`${providerTitle(provider as Provider)} connected successfully.`);
      refreshIntegrations();
    }

    if (provider && oauthStatus === "error") {
      setError(`${providerTitle(provider as Provider)} connection failed.`);
    }

    if (provider || oauthStatus) {
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams, refreshIntegrations]);

  async function handleConnect(provider: Provider) {
    setBusyProvider(provider);
    setError(null);
    setNotice(null);

    try {
      const { url } = await startIntegration(provider);

      if (url.startsWith("/mock-oauth/")) {
        setIntegrationConnected(provider, true);
        setNotice(`${providerTitle(provider)} connected successfully.`);
        return;
      }

      window.location.href = url;
    } catch (err) {
      console.error(err);
      setError(`Failed to start ${providerTitle(provider)} connection.`);
    } finally {
      setBusyProvider(null);
    }
  }

  async function handleDisconnect(provider: Provider) {
    setBusyProvider(provider);
    setError(null);
    setNotice(null);

    try {
      await disconnectIntegration(provider);
      setIntegrationConnected(provider, false);
      setNotice(`${providerTitle(provider)} disconnected.`);
    } catch (err) {
      console.error(err);
      setError(`Failed to disconnect ${providerTitle(provider)}.`);
    } finally {
      setBusyProvider(null);
    }
  }

  const continueToDashboard = () => {
    nav("/dashboard", { replace: true });
  };

  return (
    <div className="min-h-screen flex flex-col font-sans antialiased relative overflow-hidden">
      <LandingHeader isLoggedIn={true} />

      <main className="flex-grow flex items-center justify-center pt-24 pb-12 px-6 relative z-10">
        <div className="max-w-4xl w-full bg-white/15 backdrop-blur-3xl border border-white/30 shadow-xl rounded-[48px] p-10 md:p-14">
          <div className="mb-12 text-center md:text-left">
            <h1 className="text-4xl md:text-3xl font-serif font-black text-brand-deep mb-4 leading-[1.1]">
              Connect your work accounts
            </h1>
            <p className="text-lg text-brand-deep/90 max-w-2xl font-medium mb-4">
              Add Slack/Gmail/Outlook so SentinelAI can monitor early burnout signals using consent-based,
              company-approved data sources.
            </p>
          </div>

          {status === "loading" && (
            <div className="mb-6 text-sm font-semibold text-brand-deep/70">
              Loading integrations...
            </div>
          )}

          {notice && (
            <div className="mb-6 text-sm font-semibold text-green-700">
              {notice}
            </div>
          )}

          {error && (
            <div className="mb-6 text-sm font-semibold text-red-600">
              {error}
            </div>
          )}

          <div className="flex flex-col gap-4 mb-12">
            {providers.map((p) => {
              const integration = integrations.find((i) => i.provider === p);
              const isConnected = integration?.connected;
              const isBusy = busyProvider === p;

              return (
                <div
                  key={p}
                  className="group relative flex flex-col md:flex-row items-center justify-between p-6 md:p-8 rounded-[32px] bg-white/30 border border-white/50 shadow-sm transition-all duration-500 hover:shadow-xl hover:bg-white/60 hover:-translate-y-1"
                >
                  <div className="flex flex-col md:flex-row items-center gap-6 text-center md:text-left">
                    <div className="w-14 h-14 flex items-center justify-center p-3 rounded-2xl bg-white/50 border border-white transition-transform group-hover:scale-105">
                      <img src={providerLogo(p)} alt={p} className="w-full h-full object-contain" />
                    </div>

                    <div>
                      <div className="flex items-center justify-center md:justify-start gap-3 mb-1">
                        <h3 className="text-xl font-bold text-brand-deep tracking-tight">
                          {providerTitle(p)}
                        </h3>
                        {isConnected && (
                          <span className="text-[9px] font-black uppercase tracking-widest text-green-700 bg-green-100/80 px-2 py-0.5 rounded-md">
                            Connected
                          </span>
                        )}
                      </div>
                      <p className="text-[15px] text-brand-deep/80 font-medium leading-relaxed max-w-md">
                        {providerDesc(p)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-6 md:mt-0 flex flex-row items-center gap-4">
                    {isConnected ? (
                      <Button
                        onClick={() => handleDisconnect(p)}
                        className="min-w-[120px] px-6 py-2.5 text-xs font-bold"
                        variant="secondary"
                        disabled={isBusy}
                      >
                        {isBusy ? "Working..." : "Disconnect"}
                      </Button>
                    ) : (
                      <Button
                        onClick={() => handleConnect(p)}
                        className="min-w-[120px] px-6 py-2.5 text-xs font-bold"
                        variant="primary"
                        disabled={isBusy}
                      >
                        {isBusy ? "Working..." : "Connect"}
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="bg-brand-deep/[0.02] border border-brand-deep/5 rounded-[32px] py-6 px-10 flex flex-col lg:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3 flex-grow">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse shrink-0" />
              <p className="text-[10px] text-brand-deep/70 font-bold uppercase tracking-widest leading-relaxed max-w-2xl">
                Only consent-based, company-approved data sources are analysed. HR decisions remain human-in-the-loop.
              </p>
            </div>

            <div className="flex flex-row items-center gap-4 shrink-0">
              <Button
                onClick={continueToDashboard}
                variant="secondary"
                className="whitespace-nowrap px-6 py-3 text-sm font-bold opacity-70 hover:opacity-100 transition-all"
              >
                Skip for now
              </Button>

              <Button
                onClick={continueToDashboard}
                disabled={!integrations.some((i) => i.connected)}
                className="whitespace-nowrap px-8 py-3 text-sm font-black shadow-[0_20px_40px_-10px_rgba(0,0,0,0.1)] hover:shadow-none transition-all"
              >
                Continue
              </Button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
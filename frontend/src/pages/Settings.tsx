import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useOnboarding } from "../state/onboarding";
import { startPersonalGmail } from "../api";
import SidebarLink from "../components/SidebarLink";
import Button from "../components/Button";
import Input from "../components/Input";

import SectionCard from "../components/settings/SectionCard";
import BillingHistoryTable from "../components/settings/BillingHistoryTable";

import SecuritySettings from "../components/settings/SecuritySettings";
import NotificationsPreferences from "../components/settings/NotificationsPreferences";
import DangerZone from "../components/settings/DangerZone";
import IntegrationsPanel from "../components/settings/integrations/IntegrationsPanel";

import { useCompany } from "../hooks/useCompany";
import { useCurrentUser } from "../hooks/useCurrentUser";

const BRAND_ORANGE = "var(--color-top)";
const PAYMENTS_URL = import.meta.env.VITE_PAYMENTS_URL ?? "https://sentinelai.work";
console.log("[settings] PAYMENTS_URL:", PAYMENTS_URL);

export default function Settings() {
  const { signup, plan } = useOnboarding();
  const navigate = useNavigate();

  const [invoices, setInvoices] = useState<any[]>([]);
  const planPrice = plan === "paid" ? "£49" : "£0";

  const { company, status, error, isUpdating, saveCompanyName } = useCompany();
  const companyId = company?.company_id;
  const [companyNameDraft, setCompanyNameDraft] = useState(signup?.companyName || "");

  const {
    status: currentUserStatus,
    user: currentUser,
    error: currentUserError,
  } = useCurrentUser();

  const isAdmin = currentUser?.role === "admin";
  const isBiller = currentUser?.role === "biller";

  const canManageCompany = isAdmin || isBiller;
  const canManageBilling = isBiller;
  const canManageIntegrations = isAdmin || isBiller;

  useEffect(() => {
    const fetchInvoices = async () => {
      if (!companyId) { console.log("[settings] invoices skipped — no companyId"); return; }
      console.log("[settings] fetching invoices for company:", companyId);
      try {
        const res = await fetch(`${PAYMENTS_URL}/api/v1/invoices/${companyId}`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("sentinel_access_token")}`,
          },
        });
        console.log("[settings] invoices response:", res.status);
        if (!res.ok) {
          console.log("[settings] invoices unavailable — free plan or no subscription yet");
          setInvoices([]);
          return;
        }
        const data = await res.json();
        console.log("[settings] invoices count:", Array.isArray(data) ? data.length : "non-array");
        setInvoices(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error("[settings] invoices fetch failed:", err);
      }
    };
    fetchInvoices();
  }, [companyId]);

  const handlePortal = async () => {
    if (!companyId) { console.warn("[portal] no companyId"); return alert("No company ID found"); }
    const endpoint = `${PAYMENTS_URL}/api/v1/portal/${companyId}`;
    console.log("[portal] POST", endpoint);
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("sentinel_access_token")}`,
        },
      });
      console.log("[portal] response status:", res.status);
      const data = await res.json();
      console.log("[portal] response data:", data);
      if (data.portal_url) {
        console.log("[portal] redirecting to:", data.portal_url);
        window.location.href = data.portal_url;
      } else {
        console.error("[portal] no portal_url in response", data);
        alert("No portal URL returned. Check console for details.");
      }
    } catch (err) {
      console.error("[portal] fetch failed:", err);
      alert("Network error opening billing portal. Check console.");
    }
  };

  useEffect(() => {
    if (company?.company_name) setCompanyNameDraft(company.company_name);
  }, [company]);

  return (
    <div
      style={{
        background: "linear-gradient(to bottom, #20022bfd, #1a011d)",
        minHeight: "100vh",
        color: "#ffffff",
        display: "flex",
        fontFamily: "'Outfit', 'Inter', sans-serif",
        overflow: "hidden",
      }}
    >
      {/* SIDEBAR */}
      <aside
        className="hidden lg:flex flex-col w-[280px] h-screen sticky top-0 p-10 shrink-0"
        style={{
          background: "rgba(0, 0, 0, 0.4)",
          backdropFilter: "blur(30px)",
          borderRight: "1px solid rgba(255, 255, 255, 0.05)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            marginBottom: "50px",
          }}
        >
          <img
            src="/logo-text.png"
            alt="SentinelAI"
            style={{ height: "30px", marginBottom: "40px", paddingLeft: "20px", filter: "brightness(0) invert(1)" }}
          />
        </div>

        <nav style={{ flexGrow: 1 }}>
          <SidebarLink to="/dashboard" label="Dashboard" />
          <SidebarLink to="/employees" label="Employees" />
          <SidebarLink to="/settings" label="Account Settings" end />
        </nav>

      </aside>

      {/* MAIN */}
      <main className="flex-grow min-w-0 p-4 md:p-10 lg:p-[60px] overflow-y-auto h-screen relative">
        <header className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 mb-12">
          <h1 style={{ fontSize: "38px", fontWeight: "900", margin: 0, letterSpacing: "-1px" }}>
            Account <span style={{ color: BRAND_ORANGE }}>Settings</span>
          </h1>

          <div className="flex flex-wrap gap-3">
            <Button 
              onClick={() => navigate("/usage?theme=dark")}
              className="!bg-white/5 !text-white/85 !border-white/30 !w-auto !px-6 !py-2 !text-xs"
              variant="secondary"
            >
              USAGE GUIDE
            </Button>
            <Button 
              onClick={() => navigate("/connect-accounts?theme=dark")}
              className="!bg-orange-500/10 !text-orange-400 !border-orange-400/40 !w-auto !px-6 !py-2 !text-xs"
              variant="secondary"
            >
              CONNECT ACCOUNTS
            </Button>
          </div>
        </header>

        {status === "loading" && (
          <div style={{ marginBottom: "20px", opacity: 0.7, fontWeight: 700 }}>
            Loading company details...
          </div>
        )}
        
        {error && (
          <div style={{ marginBottom: "20px", color: BRAND_ORANGE, fontWeight: 800 }}>
            {error}
          </div>
        )}

        {currentUserStatus === "loading" && (
          <div style={{ marginBottom: "20px", opacity: 0.7, fontWeight: 700 }}>
            Loading current user...
          </div>
        )}
        
        {currentUserError && (
          <div style={{ marginBottom: "20px", color: BRAND_ORANGE, fontWeight: 800 }}>
            {currentUserError}
          </div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-10">
          {/* LEFT COLUMN */}
          <div className="space-y-8">
            {/* Identity */}
            <SectionCard title="Identity & Access">
              <div className="space-y-6">
                <Input
                  label="Admin Full Name"
                  defaultValue={currentUser?.display_name || signup?.adminName || ""}
                />

                <Input
                  label="Company Email"
                  defaultValue={currentUser?.email || signup?.adminEmail || ""}
                />

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "14px",
                  }}
                >
                  <div
                    style={{
                      padding: "14px 18px",
                      borderRadius: "18px",
                      background: "rgba(255,255,255,0.04)",
                      border: "1px solid rgba(255,255,255,0.06)",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "10px",
                        fontWeight: 900,
                        letterSpacing: "1px",
                        textTransform: "uppercase",
                        opacity: 0.45,
                        marginBottom: "6px",
                      }}
                    >
                      Role
                    </div>
                    <div style={{ fontSize: "14px", fontWeight: 800 }}>
                      {currentUser?.role?.toUpperCase() || "UNKNOWN"}
                    </div>
                  </div>
                  
                  <div
                    style={{
                      padding: "14px 18px",
                      borderRadius: "18px",
                      background: "rgba(255,255,255,0.04)",
                      border: "1px solid rgba(255,255,255,0.06)",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "10px",
                        fontWeight: 900,
                        letterSpacing: "1px",
                        textTransform: "uppercase",
                        opacity: 0.45,
                        marginBottom: "6px",
                      }}
                    >
                      Account Status
                    </div>
                    <div style={{ fontSize: "14px", fontWeight: 800 }}>
                      {currentUser?.status?.toUpperCase() || "UNKNOWN"}
                    </div>
                  </div>
                </div>

                <Input
                  label="Company Name"
                  value={companyNameDraft}
                  onChange={(e) => setCompanyNameDraft(e.target.value)}
                />

                <Button
                  variant="secondary"
                  className="!text-white !bg-white/20 hover:!bg-white/30 border-white/10"
                  style={{ width: "auto", padding: "12px 30px", marginTop: "10px" }}
                  onClick={() => saveCompanyName(companyNameDraft)}
                  disabled={isUpdating || !canManageCompany}
                >
                  {isUpdating ? "Updating..." : "Update Profile"}
                </Button>
              </div>
            </SectionCard>

            {/* Subscription */}
            <SectionCard title="Active Subscription">
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: "20px",
                }}
              >
                <div>
                  <p style={{ margin: 0, fontSize: "18px", fontWeight: "800" }}>
                    {plan?.toUpperCase() || "FREE"} PLAN
                  </p>

                  <p style={{ margin: 0, fontSize: "12px", opacity: 0.5 }}>
                    {planPrice} / month
                  </p>
                </div>

                <div style={{ textAlign: "right" }}>
                  <p style={{ margin: 0, fontSize: "18px", fontWeight: "800" }}>
                    50 Slots
                  </p>

                  <p style={{ margin: 0, fontSize: "12px", opacity: 0.5 }}>
                    Current Capacity
                  </p>
                </div>
              </div>

              {canManageBilling && (
                <>
                  <Button
                    variant="ghost"
                    className="!text-white border-white/20 hover:border-white/40"
                    onClick={() => navigate("/plan")}
                  >
                    Change Plan for Next Cycle
                  </Button>

                  <BillingHistoryTable invoices={invoices} />
                </>
              )}
            </SectionCard>

            <SectionCard title="Security">
              <SecuritySettings />
            </SectionCard>
          </div>

          {/* RIGHT COLUMN */}
          <div className="space-y-8">
            {canManageBilling && (
              <SectionCard title="Payment Methods">
                <p style={{ opacity: 0.6, fontSize: "13px", marginBottom: "16px" }}>
                  Manage your payment methods and billing details securely via Stripe.
                </p>

                <Button
                  onClick={handlePortal}
                  variant="secondary"
                  className="!text-white !bg-white/10 !border-white/30"
                >
                  Manage Billing $ Cards (Stripe)
                </Button>

                <p
                  style={{
                    fontSize: "11px",
                    opacity: 0.4,
                    marginTop: "20px",
                    textAlign: "center",
                  }}
                >
                  PAYMENTS ARE SECURELY HANDLED BY STRIPE
                </p>
              </SectionCard>
                )}

            <SectionCard title="Notifications">
              <NotificationsPreferences />
            </SectionCard>

            {!canManageIntegrations && currentUser?.role === "viewer" && (
              <SectionCard title="My Gmail">
                <p style={{ opacity: 0.6, fontSize: "13px", marginBottom: "16px" }}>
                  Connect your own Gmail so SentinelAI can monitor your mailbox as part of company-wide consent-based analysis.
                </p>
                <Button
                  variant="secondary"
                  className="!text-white !bg-white/10 !border-white/30"
                  onClick={async () => {
                    try {
                      const { url } = await startPersonalGmail();
                      window.location.href = url;
                    } catch {
                      alert("Failed to start Gmail connection. Please try again.");
                    }
                  }}
                >
                  Connect Gmail
                </Button>
              </SectionCard>
            )}

            {canManageIntegrations && companyId && (
              <SectionCard title="Team Gmail Registration">
                <p style={{ opacity: 0.6, fontSize: "13px", marginBottom: "16px", lineHeight: 1.6 }}>
                  Share this link with your team in Slack. Each member clicks it and connects
                  their own Gmail — no SentinelAI account needed.
                </p>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    background: "rgba(255,255,255,0.06)",
                    border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: "14px",
                    padding: "12px 16px",
                  }}
                >
                  <code
                    style={{
                      flex: 1,
                      fontSize: "12px",
                      fontFamily: "monospace",
                      opacity: 0.85,
                      wordBreak: "break-all",
                    }}
                  >
                    {`${window.location.origin}/register-gmail?company_id=${companyId}`}
                  </code>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(
                        `${window.location.origin}/register-gmail?company_id=${companyId}`
                      );
                    }}
                    style={{
                      background: "rgba(227,141,38,0.18)",
                      color: BRAND_ORANGE,
                      border: "1px solid rgba(227,141,38,0.35)",
                      borderRadius: "8px",
                      padding: "6px 12px",
                      fontSize: "11px",
                      fontWeight: 900,
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                    }}
                  >
                    COPY
                  </button>
                </div>
              </SectionCard>
            )}

            {canManageIntegrations ? (
              <SectionCard title="Connected Integrations">
                <IntegrationsPanel />
              </SectionCard>
            ) : (
              <SectionCard title="Connected Integrations">
                <p style={{ opacity: 0.7, lineHeight: 1.6 }}>
                  You have read-only access. Connected providers can be reviewed here, but only
          admins and billers can modify integrations.
                </p>
              </SectionCard>
            )}
            
            {canManageBilling && <DangerZone />}
          </div>
        </div>
        <div className="h-24 lg:hidden" />
      </main>

      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 px-6 py-4 flex justify-around items-center" 
        style={{
          background: "rgba(20, 1, 22, 0.9)",
          backdropFilter: "blur(20px)",
          borderTop: "1px solid rgba(255, 255, 255, 0.1)",
        }}
        >
        <SidebarLink to="/dashboard" label="Home" end />
        <SidebarLink to="/employees" label="Employees" />
        <SidebarLink to="/settings" label="Settings" />
      </nav>

    </div>
  );
}
import { useOnboarding } from "../state/onboarding";
import SidebarLink from "../components/SidebarLink";
import Button from "../components/Button";
import Input from "../components/Input";

import SectionCard from "../components/settings/SectionCard";
import PaymentMethodsList from "../components/settings/PaymentMethodsList";
import BillingHistoryTable from "../components/settings/BillingHistoryTable";

import SecuritySettings from "../components/settings/SecuritySettings";
import NotificationsPreferences from "../components/settings/NotificationsPreferences";
import DangerZone from "../components/settings/DangerZone";

import { MOCK_CARDS, MOCK_INVOICES } from "../state/settingsMock";

const BRAND_ORANGE = "var(--color-top)";

export default function Settings() {
  const { signup, plan, reset } = useOnboarding();
  const planPrice = plan === "paid" ? "$29" : "$0";

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
        style={{
          width: "280px",
          height: "100vh",
          background: "rgba(0, 0, 0, 0.4)",
          backdropFilter: "blur(30px)",
          borderRight: "1px solid rgba(255, 255, 255, 0.05)",
          display: "flex",
          flexDirection: "column",
          padding: "40px 20px",
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
            style={{ height: "30px", marginBottom: "40px", paddingLeft: "20px" }}
          />
        </div>

        <nav style={{ flexGrow: 1 }}>
          <SidebarLink to="/dashboard" label="Dashboard" />
          <SidebarLink to="/employees" label="Employees" />
          <SidebarLink to="/connect-accounts" label="Connected Accounts" />
          <SidebarLink to="/usage" label="Usage Guide" />
          <SidebarLink to="/settings" label="Account Settings" end />
        </nav>

        <button
          onClick={reset}
          style={{
            background: "transparent",
            border: "1px solid rgba(255,255,255,0.1)",
            color: "rgba(255,255,255,0.4)",
            padding: "10px",
            borderRadius: "8px",
            cursor: "pointer",
            fontSize: "11px",
            fontWeight: "bold",
          }}
        >
          RESET SYSTEM
        </button>
      </aside>

      {/* MAIN */}
      <main
        style={{
          flexGrow: 1,
          padding: "50px 60px",
          overflowY: "auto",
          height: "100vh",
        }}
      >
        <header style={{ marginBottom: "50px" }}>
          <h1
            style={{
              fontSize: "38px",
              fontWeight: "900",
              margin: 0,
              letterSpacing: "-1px",
            }}
          >
            Account <span style={{ color: BRAND_ORANGE }}>Settings</span>
          </h1>
        </header>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "40px",
          }}
        >
          {/* LEFT COLUMN */}
          <div className="space-y-8">
            {/* Identity */}
            <SectionCard title="Identity & Access">
              <div className="space-y-6">
                <Input
                  label="Admin Full Name"
                  defaultValue={signup?.adminName || ""}
                />

                <Input
                  label="Company Email"
                  defaultValue={signup?.adminEmail || ""}
                />

                <Input
                  label="Company Name"
                  defaultValue={signup?.companyName || ""}
                />

                <Button
                  variant="secondary"
                  className="!text-white !bg-white/20 hover:!bg-white/30 border-white/10"
                  style={{ width: "auto", padding: "12px 30px", marginTop: "10px" }}
                >
                  Update Profile
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

              <Button
                variant="ghost"
                className="!text-white border-white/20 hover:border-white/40"
              >
                Change Plan for Next Cycle
              </Button>

              <BillingHistoryTable invoices={MOCK_INVOICES} />
            </SectionCard>
          </div>

          {/* RIGHT COLUMN */}
          <SectionCard title="Payment Methods">
            <PaymentMethodsList cards={MOCK_CARDS} />

            {MOCK_CARDS.length < 3 && (
              <Button
                variant="secondary"
                className="!text-white !bg-white/10 !border-dashed border-white/30 hover:!bg-white/20"
              >
                + Add New Payment Method
              </Button>
            )}

            <p
              style={{
                fontSize: "11px",
                opacity: 0.4,
                marginTop: "20px",
                textAlign: "center",
              }}
            >
              MINIMUM 2 PAYMENT METHODS REQUIRED.
            </p>
          </SectionCard>

          <SectionCard title="Security">
            <SecuritySettings />
          </SectionCard>
          
          <SectionCard title="Notifications">
            <NotificationsPreferences />
          </SectionCard>
          
          <DangerZone />
        </div>
      </main>
    </div>
  );
}
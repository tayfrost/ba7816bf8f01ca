import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
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
import IntegrationsPanel from "../components/settings/integrations/IntegrationsPanel";

import { MOCK_CARDS, MOCK_INVOICES } from "../state/settingsMock";

import { useCompany } from "../hooks/useCompany";
import { useTeamUsers } from "../hooks/useTeamUsers";
import { useCurrentUser } from "../hooks/useCurrentUser";

const BRAND_ORANGE = "var(--color-top)";

export default function Settings() {
  const { signup, plan, reset } = useOnboarding();
  const navigate = useNavigate();
  const planPrice = plan === "paid" ? "$29" : "$0";

  const {
    users,
    status: usersStatus,
    error: usersError,
    busyUserId,
    changeRole,
    removeUser,
    invite,
  } = useTeamUsers();

  const { company, status, error, isUpdating, saveCompanyName } = useCompany();
  const [companyNameDraft, setCompanyNameDraft] = useState(signup?.companyName || "");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteSurname, setInviteSurname] = useState("");
  const [inviteRole, setInviteRole] = useState<"admin" | "biller" | "viewer">("viewer");
  const {
    status: currentUserStatus,
    user: currentUser,
    error: currentUserError,
  } = useCurrentUser();

  const isAdmin = currentUser?.role === "admin";
  const isBiller = currentUser?.role === "biller";

  const canManageCompany = isAdmin || isBiller;
  const canManageTeam = isAdmin || isBiller;
  const canManageBilling = isBiller;
  const canManageIntegrations = isAdmin || isBiller;

  useEffect(() => {
    if (company?.company_name) {
      setCompanyNameDraft(company.company_name);
    }
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

        <div style={{ position: "absolute", top: "50px", right: "60px", display: "flex", gap: "15px" }}>
          <Button 
            onClick={() => navigate("/connect-accounts")}
            className="!bg-orange-500/20 !text-orange-400 !border-orange-500/40 !w-auto !px-6 !py-2 !text-xs"
            variant="secondary"
          >
            CONNECT ACCOUNTS
          </Button>
          <Button 
            onClick={() => navigate("/usage")}
            className="!bg-orange-500/20 !text-orange-400 !border-orange-500/40 !w-auto !px-6 !py-2 !text-xs"
            variant="secondary"
          >
            USAGE GUIDE
          </Button>
        </div>

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
                  defaultValue={
                    currentUser
                      ? `${currentUser.name} ${currentUser.surname}`.trim()
                      : signup?.adminName || ""
                  }
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
                  >
                    Change Plan for Next Cycle
                  </Button>

                  <BillingHistoryTable invoices={MOCK_INVOICES} />
                </>
              )}
            </SectionCard>
          </div>

          {/* RIGHT COLUMN */}
          {canManageBilling && (
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
              )}

          <SectionCard title="Security">
            <SecuritySettings />
          </SectionCard>
          
          <SectionCard title="Notifications">
            <NotificationsPreferences />
          </SectionCard>

          <SectionCard title="Team Members">
            
            {usersStatus === "loading" && (
              <p style={{ opacity: 0.6 }}>Loading team members...</p>
            )}
            
            {usersError && (
              <p style={{ color: BRAND_ORANGE }}>{usersError}</p>
            )}

            {canManageTeam && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1.3fr 1fr 1fr 0.8fr auto",
                gap: "10px",
                marginBottom: "20px",
                paddingBottom: "20px",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <input
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="email"
                style={{
                  background: "rgba(255,255,255,0.08)",
                  color: "white",
                  border: "1px solid rgba(255,255,255,0.15)",
                  borderRadius: "10px",
                  padding: "10px 12px",
                  fontSize: "12px",
                }}
              />

              <input
                value={inviteName}
                onChange={(e) => setInviteName(e.target.value)}
                placeholder="name"
                style={{
                  background: "rgba(255,255,255,0.08)",
                  color: "white",
                  border: "1px solid rgba(255,255,255,0.15)",
                  borderRadius: "10px",
                  padding: "10px 12px",
                  fontSize: "12px",
                }}
              />

              <input
                value={inviteSurname}
                onChange={(e) => setInviteSurname(e.target.value)}
                placeholder="surname"
                style={{
                  background: "rgba(255,255,255,0.08)",
                  color: "white",
                  border: "1px solid rgba(255,255,255,0.15)",
                  borderRadius: "10px",
                  padding: "10px 12px",
                  fontSize: "12px",
                }}
              />

              <select
                value={inviteRole}
                onChange={(e) =>
                  setInviteRole(e.target.value as "admin" | "biller" | "viewer")
                }
                style={{
                  background: "rgba(255,255,255,0.08)",
                  color: "white",
                  border: "1px solid rgba(255,255,255,0.15)",
                  borderRadius: "10px",
                  padding: "10px 12px",
                  fontSize: "12px",
                  fontWeight: 800,
                }}
              >
                <option value="viewer">VIEWER</option>
                <option value="admin">ADMIN</option>
                <option value="biller">BILLER</option>
              </select>

              <button
                onClick={async () => {
                  if (!inviteEmail || !inviteName || !inviteSurname) return;

                  await invite({
                    email: inviteEmail,
                    name: inviteName,
                    surname: inviteSurname,
                    role: inviteRole,
                  });

                  setInviteEmail("");
                  setInviteName("");
                  setInviteSurname("");
                  setInviteRole("viewer");
                }}
                style={{
                  background: "rgba(227,141,38,0.18)",
                  color: BRAND_ORANGE,
                  border: "1px solid rgba(227,141,38,0.35)",
                  borderRadius: "10px",
                  padding: "10px 14px",
                  fontSize: "11px",
                  fontWeight: 900,
                  cursor: "pointer",
                }}
              >
                INVITE
              </button>
            </div>
            )}
            
            {users.map((user) => (
              <div
                key={user.user_id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "10px 0",
                  borderBottom: "1px solid rgba(255,255,255,0.05)",
                }}
              >
                <div>
                  <div style={{ fontWeight: 700 }}>
                    {user.name} {user.surname}
                  </div>
                  
                  <div style={{ fontSize: "12px", opacity: 0.6 }}>
                    {user.email}
                  </div>
                </div>
                
                {canManageTeam ? (
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <select
                      value={user.role}
                      onChange={(e) =>
                        changeRole(
                          user.user_id,
                          e.target.value as "admin" | "biller" | "viewer"
                        )
                      }
                      disabled={busyUserId === user.user_id}
                      style={{
                        background: "rgba(255,255,255,0.08)",
                        color: "white",
                        border: "1px solid rgba(255,255,255,0.15)",
                        borderRadius: "10px",
                        padding: "8px 10px",
                        fontSize: "12px",
                        fontWeight: 800,
                      }}
                    >
                      <option value="viewer">VIEWER</option>
                      <option value="admin">ADMIN</option>
                      <option value="biller">BILLER</option>
                    </select>

                    <button
                      onClick={() => removeUser(user.user_id)}
                      disabled={busyUserId === user.user_id}
                      style={{
                        background: "rgba(255,80,80,0.15)",
                        color: "#ff8a8a",
                        border: "1px solid rgba(255,80,80,0.25)",
                        borderRadius: "10px",
                        padding: "8px 12px",
                        fontSize: "11px",
                        fontWeight: 900,
                        cursor: "pointer",
                      }}
                    >
                      {busyUserId === user.user_id ? "..." : "REMOVE"}
                    </button>
                  </div>
                ) : (
                  <div style={{ fontSize: "12px", fontWeight: 800, opacity: 0.8}}>
                    {user.role.toUpperCase()}
                  </div>
                )}
              </div>
            ))}
            
          </SectionCard>

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
      </main>
    </div>
  );
}
import { useOnboarding } from "../state/onboarding";
import SidebarLink from "../components/SidebarLink";
import Button from "../components/Button";
import Input from "../components/Input";

const BRAND_ORANGE = "var(--color-top)";

const MOCK_CARDS = [
  { id: 1, name: "J. DOE (CORPORATE)", lastFour: "4242", isDefault: true },
  { id: 2, name: "SENTINEL ADMIN", lastFour: "8891", isDefault: false },
];

export default function Settings() {
  const { signup, plan, reset } = useOnboarding();
  const planPrice = plan === "paid" ? "$29" : "$0";

  return (
    <div style={{
      background: "linear-gradient(to bottom, #20022bfd, #1a011d)",
      minHeight: "100vh",
      color: "#ffffff",
      display: "flex",
      fontFamily: "'Outfit', 'Inter', sans-serif",
      overflow: "hidden"
    }}>
      
      <aside style={{
        width: "280px",
        height: "100vh",
        background: "rgba(0, 0, 0, 0.4)",
        backdropFilter: "blur(30px)",
        borderRight: "1px solid rgba(255, 255, 255, 0.05)",
        display: "flex",
        flexDirection: "column",
        padding: "40px 20px"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "50px" }}>
          <img src="/logo-text.png" alt="SentinelAI" style={{ height: "30px", marginBottom: "40px", paddingLeft: "20px" }} />
        </div>

        <nav style={{ flexGrow: 1 }}>
          <SidebarLink to="/dashboard" label="Dashboard" />
          <SidebarLink to="/employees" label="Employees" />
          <SidebarLink to="/connect-accounts" label="Connected Accounts" />
          <SidebarLink to="/usage" label="Usage Guide" />
          <SidebarLink to="/settings" label="Account Settings" end />
        </nav>

        <button onClick={reset} style={{ 
          background: "transparent", border: "1px solid rgba(255,255,255,0.1)", 
          color: "rgba(255,255,255,0.4)", padding: "10px", borderRadius: "8px", cursor: "pointer", fontSize: "11px", fontWeight: "bold"
        }}>
          RESET SYSTEM
        </button>
      </aside>

      <main style={{ flexGrow: 1, padding: "50px 60px", overflowY: "auto", height: "100vh" }}>
        
        <header style={{ marginBottom: "50px" }}>
          <h1 style={{ fontSize: "38px", fontWeight: "900", margin: 0, letterSpacing: "-1px" }}>
            Account <span style={{ color: BRAND_ORANGE }}>Settings</span>
          </h1>
        </header>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "40px" }}>
          
          <div className="space-y-8">
            <section style={{ background: "rgba(255,255,255,0.03)", padding: "40px", borderRadius: "35px", border: "1px solid rgba(255,255,255,0.08)" }}>
              <h3 style={{ fontSize: "14px", fontWeight: "900", color: BRAND_ORANGE, letterSpacing: "2px", textTransform: "uppercase", marginBottom: "30px" }}>
                Identity & Access
              </h3>
              <div className="space-y-6">
                <Input label="Admin Full Name" defaultValue={signup?.adminName || ""} />
                <Input label="Company Email" defaultValue={signup?.adminEmail || ""} />
                <Input label="Company Name" defaultValue={signup?.companyName || ""} />
                
                <Button 
                  variant="secondary" 
                  className="!text-white !bg-white/20 hover:!bg-white/30 border-white/10"
                  style={{ width: "auto", padding: "12px 30px", marginTop: "10px" }}
                >
                  Update Profile
                </Button>
              </div>
            </section>

            <section style={{ background: "rgba(255,255,255,0.03)", padding: "40px", borderRadius: "35px", border: "1px solid rgba(255,255,255,0.08)" }}>
              <h3 style={{ fontSize: "14px", fontWeight: "900", color: BRAND_ORANGE, letterSpacing: "2px", textTransform: "uppercase", marginBottom: "30px" }}>
                Active Subscription
              </h3>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "20px" }}>
                <div>
                  <p style={{ margin: 0, fontSize: "18px", fontWeight: "800" }}>{plan?.toUpperCase() || "FREE"} PLAN</p>
                  <p style={{ margin: 0, fontSize: "12px", opacity: 0.5 }}>{planPrice} / month</p>
                </div>
                <div style={{ textAlign: "right" }}>
                  <p style={{ margin: 0, fontSize: "18px", fontWeight: "800" }}>50 Slots</p>
                  <p style={{ margin: 0, fontSize: "12px", opacity: 0.5 }}>Current Capacity</p>
                </div>
              </div>

              <Button 
                variant="ghost" 
                className="!text-white border-white/20 hover:border-white/40"
              >
                Change Plan for Next Cycle
              </Button>
            </section>
          </div>

          <section style={{ background: "rgba(255,255,255,0.03)", padding: "40px", borderRadius: "35px", border: "1px solid rgba(255,255,255,0.08)" }}>
            <h3 style={{ fontSize: "14px", fontWeight: "900", color: BRAND_ORANGE, letterSpacing: "2px", textTransform: "uppercase", marginBottom: "30px" }}>
              Payment Methods
            </h3>
            
            <div className="space-y-4 mb-8">
              {MOCK_CARDS.map(card => (
                <div key={card.id} style={{ 
                  background: "rgba(255,255,255,0.05)", 
                  padding: "20px 25px", 
                  borderRadius: "20px", 
                  display: "flex", 
                  justifyContent: "space-between", 
                  alignItems: "center",
                  border: card.isDefault ? `1px solid ${BRAND_ORANGE}` : "1px solid transparent"
                }}>
                  <div>
                    <p style={{ margin: 0, fontSize: "14px", fontWeight: "800" }}>Visa ending in {card.lastFour}</p>
                    <p style={{ margin: 0, fontSize: "11px", opacity: 0.5 }}>{card.name}</p>
                  </div>
                  {card.isDefault && <span style={{ fontSize: "10px", fontWeight: "900", color: BRAND_ORANGE }}>DEFAULT</span>}
                </div>
              ))}
            </div>

            {MOCK_CARDS.length < 3 && (
              <Button 
                variant="secondary" 
                className="!text-white !bg-white/10 !border-dashed border-white/30 hover:!bg-white/20"
              >
                + Add New Payment Method
              </Button>
            )}
            
            <p style={{ fontSize: "11px", opacity: 0.4, marginTop: "20px", textAlign: "center" }}>
              MINIMUM 2 PAYMENT METHODS REQUIRED.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
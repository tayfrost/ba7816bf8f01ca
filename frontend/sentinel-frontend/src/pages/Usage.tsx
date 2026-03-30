import { useNavigate, useSearchParams } from "react-router-dom"; // Added useSearchParams
import Stepper from "../components/Stepper";
import Button from "../components/Button";
import LandingHeader from "../components/LandingHeader";

export default function Usage() {
  const nav = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams(); // Added
  
  const isDark = searchParams.get("theme") === "dark"; // Added

  const StepItem = ({ number, text }: { number: string; text: string }) => (
    <div 
      style={{ background: "var(--dynamic-card)", borderColor: "var(--dynamic-border)" }} // Updated
      className="border rounded-[32px] p-8 flex items-center gap-8 backdrop-blur-md shadow-sm"
    >
      <div style={{
        minWidth: "48px",
        height: "48px",
        borderRadius: "14px",
        background: "var(--color-brand-deep)",
        color: "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: "900",
        fontSize: "18px",
      }}>
        {number}
      </div>
      <p style={{ color: "var(--dynamic-text)" }} className="text-xl font-semibold leading-relaxed"> {/* Updated color */}
        {text}
      </p>
    </div>
  );

  return (
    <div 
      className={`min-h-screen overflow-y-auto font-sans transition-colors duration-500 ${isDark ? 'theme-dark' : ''}`} // Added theme class
    >
      <LandingHeader 
        isLoggedIn={true} 
        theme={isDark ? 'dark' : 'light'} 
        onToggleTheme={() => setSearchParams({ theme: isDark ? 'light' : 'dark' })} // Added toggle logic
      />

      <div className="max-w-4xl mx-auto px-6 pt-32 pb-24">
        <div className="flex flex-col items-center mb-12">
          <Stepper currentPath="/usage" />
        </div>

        <div 
          style={{ background: "var(--dynamic-card)", borderColor: "var(--dynamic-border)" }} // Updated
          className="backdrop-blur-3xl p-12 rounded-[2.5rem] border shadow-2xl"
        >
          <header className="mb-12">
            <h1 style={{ color: "var(--dynamic-text)" }} className="text-4xl md:text-3xl font-serif font-black mb-4"> {/* Updated color */}
              How to use SentinelAI
            </h1>
            <p style={{ color: "var(--dynamic-text)", opacity: 0.7 }} className="text-lg font-medium max-w-3xl"> {/* Updated color */}
              SentinelAI is a consent-based early warning system for burnout risk. Follow these steps to set up
              and interpret your organisation’s dashboard.
            </p>
          </header>

          <h2 style={{ color: "var(--dynamic-text)", opacity: 0.75 }} className="text-sm uppercase tracking-[0.2em] font-bold mb-6 ml-2"> {/* Updated color */}
            Setup steps
          </h2>

          <div className="flex flex-col gap-4">
            <StepItem number="1" text="Connect your work accounts (Slack/Gmail/Outlook) via the Connect Accounts page." />
            <StepItem number="2" text="Open the Dashboard to view metrics and trends over time." />
            <StepItem number="3" text="Use Week/Month/Year/All Time/Custom ranges to explore patterns." />
            <StepItem number="4" text="Review alerts for potential risk signals and investigate context." />
          </div>

          <div className="mt-12 bg-white/5 border border-white/10 rounded-[32px] py-8 px-10 flex flex-col md:flex-row items-center justify-between gap-6 md:gap-4">
            <div className="flex items-center gap-4 flex-[1.5]">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse shrink-0" />
              <p style={{ color: "var(--dynamic-text)", opacity: 0.7 }} className="text-[10px] font-bold uppercase tracking-widest leading-[1.6] max-w-md"> {/* Updated color */}
                WHEN YOU'RE READY, GO TO THE DASHBOARD TO VIEW ORGANISATION METRICS.
              </p>
            </div>

            <div className="flex items-center gap-4 shrink-0">
              <button 
                onClick={() => nav(`/connect-accounts${isDark ? '?theme=dark' : ''}`)} // Persist theme on nav
                className="whitespace-nowrap px-8 py-3.5 text-sm font-bold text-brand-deep bg-white border border-brand-deep/10 rounded-xl hover:bg-white/40 transition-all shadow-sm"
              >
                Connect Accounts
              </button>
              
              <div className="min-w-[180px]">
                <Button variant="primary" onClick={() => nav("/dashboard")}>
                  Go to Dashboard
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
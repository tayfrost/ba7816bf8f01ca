import { useNavigate } from "react-router-dom";
import Stepper from "../components/Stepper";
import Button from "../components/Button";
import LandingHeader from "../components/LandingHeader";

export default function Usage() {
  const nav = useNavigate();

  const StepItem = ({ number, text }: { number: string; text: string }) => (
    <div className="bg-white/20 border border-white/40 rounded-[32px] p-8 flex items-center gap-8 backdrop-blur-md shadow-[0_10px_30px_rgba(63,3,69,0.02)]">
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
        boxShadow: "0 6px 15px rgba(227, 141, 38, 0.2)"
      }}>
        {number}
      </div>
      <p className="text-xl font-semibold text-brand-deep leading-relaxed">
        {text}
      </p>
    </div>
  );

  return (
    <div style={{ 
      position: "absolute", 
      inset: 0, 
      overflowY: "auto", 
      WebkitOverflowScrolling: "touch" 
    }} className="bg-transparent font-sans">
      
      <LandingHeader isLoggedIn={true} />

      <div className="max-w-4xl mx-auto px-6 pt-32 pb-24">
        <div className="flex flex-col items-center mb-12">
          <Stepper currentPath="/usage" />
        </div>

        <div className="bg-white/20 backdrop-blur-3xl p-10 rounded-[2.5rem] border border-white/30 shadow-2xl p-12">
          
          <header className="mb-12">
            <h1 className="text-4xl md:text-3xl font-serif font-black text-brand-deep mb-4">
              How to use SentinelAI
            </h1>
            <p className="text-lg text-brand-deep/70 font-medium max-w-3xl">
              SentinelAI is a consent-based early warning system for burnout risk. Follow these steps to set up
              and interpret your organisation’s dashboard.
            </p>
          </header>

          <h2 className="text-sm uppercase tracking-[0.2em] text-brand-deep/75 font-bold mb-6 ml-2">
            Setup steps
          </h2>

          <div className="flex flex-col gap-4">
            <StepItem number="1" text="Connect your work accounts (Slack/Gmail/Outlook) via the Connect Accounts page." />
            <StepItem number="2" text="Open the Dashboard to view metrics and trends over time." />
            <StepItem number="3" text="Use Week/Month/Year/All Time/Custom ranges to explore patterns." />
            <StepItem number="4" text="Review alerts for potential risk signals and investigate context." />
          </div>

          <div className="mt-12 bg-brand-deep/[0.03] border border-brand-deep/5 rounded-[32px] py-8 px-10 flex flex-col md:flex-row items-center justify-between gap-6 md:gap-4">
            <div className="flex items-center gap-4 flex-[1.5]">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse shrink-0" />
              <p className="text-[10px] text-brand-deep/70 font-bold uppercase tracking-widest leading-[1.6] max-w-md">
                WHEN YOU'RE READY, GO TO THE DASHBOARD TO VIEW ORGANISATION METRICS.
              </p>
            </div>

            <div className="flex items-center gap-4 shrink-0">
              <button 
                onClick={() => nav("/connect-accounts")}
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
import { useNavigate } from "react-router-dom";
import Stepper from "../components/Stepper";
import SubscriptionCard from "../components/SubscriptionCard";
import LandingHeader from "../components/LandingHeader";
import { useOnboarding } from "../state/onboarding";

export default function ChoosePlan() {
  const navigate = useNavigate();
  const { setPlan, setPlanInterval } = useOnboarding();

  function selectPlan(plan: "free" | "paid", interval: "month" | "year" = "month") {
    setPlan(plan);
    setPlanInterval(interval);
    navigate(`/signup?plan=${plan}`);
  }

  function handleLoginAsFree() {
    setPlan("free");
    setPlanInterval("month");
    navigate("/login");
  }

  return (
    <div className="h-screen w-full flex flex-col bg-transparent font-sans overflow-y-auto scroll-smooth">
      <LandingHeader onLogin={handleLoginAsFree} />

      <div className="flex flex-col items-center mt-24 mb-12 shrink-0">
        <img 
          src="/logo-icon.png" 
          alt="SentinelAI Logo" 
          className="h-32 md:h-48 w-auto mb-2 drop-shadow-2xl" 
        />
        <img 
          src="/logo-text.png" 
          alt="SentinelAI" 
          className="h-10 md:h-20 w-auto opacity-90" 
        />
        
        <div className="mt-12">
          <Stepper currentPath="/plan" />
        </div>
      </div>


      <div id="pricing" className="max-w-7xl mx-auto px-6 w-full shrink-0 scroll-mt-24">
        <div className="flex flex-wrap justify-center gap-6 md:gap-8 scale-95 md:scale-100 origin-top mt-7">
          <div onClick={() => selectPlan("free")} className="w-full max-w-[320px] cursor-pointer">
            <SubscriptionCard
              title="Free"
              price="£0"
              period=""
              features={["Standard Alerts", "7-Day History", "Basic Support"]}
            />
          </div>

          <div onClick={() => selectPlan("paid", "month")} className="w-full max-w-[320px] cursor-pointer">
            <SubscriptionCard
              title="Monthly"
              price="£49"
              period="mo"
              features={["AI Analysis", "Unlimited History", "Priority Support"]}
            />
          </div>

          <div onClick={() => selectPlan("paid", "year")} className="w-full max-w-[320px] cursor-pointer">
            <SubscriptionCard
              title="Annual"
              price="£490"
              period="yr"
              features={["Everything in Monthly", "2 Months Free", "Network Audit"]}
            />
          </div>
        </div>
      </div>

  
      <div id="features" className="max-w-5xl mx-auto px-6 w-full mt-32 mb-32 shrink-0 scroll-mt-24">
        <div className="bg-white/10 backdrop-blur-3xl border border-white/20 rounded-[3rem] p-12 shadow-2xl">
          
          <div className="text-center mb-16 border-b border-brand-deep/10 pb-12">
            <h2 className="text-3xl font-serif font-black text-brand-deep mb-6 tracking-widest">
              Wellness | Protection | Support
            </h2>
            <p className="text-xl text-brand-deep/80 leading-relaxed max-w-3xl mx-auto font-medium">
              SentinelAI acts as a digital guardian for your workspace. We detect early signs of 
              <span className="text-brand-deep font-bold"> burnout, harassment, and mental health distress</span>, 
              sending real-time alerts to HR so you can provide support when it's needed most.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-16">
            <div className="space-y-6">
              <h3 className="text-lg font-bold text-brand-deep/60 tracking-widest uppercase pb-2 border-b border-brand-deep/10">
                Intelligence
              </h3>
              <ul className="space-y-4 text-brand-deep font-medium">
                <li className="flex items-start gap-2"><span>•</span> BERT Classifier (Risk Categories)</li>
                <li className="flex items-start gap-2"><span>•</span> Agent: Harassment & Self-Harm</li>
                <li className="flex items-start gap-2"><span>•</span> Agent: Burnout & Distress Detection</li>
                <li className="flex items-start gap-2"><span>•</span> Embedding Relevance Filtering</li>
              </ul>
            </div>

            <div className="space-y-6">
              <h3 className="text-lg font-bold text-brand-deep/60 tracking-widest uppercase pb-2 border-b border-brand-deep/10">
                Infrastructure
              </h3>
              <ul className="space-y-4 text-brand-deep font-medium">
                <li className="flex items-start gap-2"><span>•</span> Frictionless Slack & Email Integration</li>
                <li className="flex items-start gap-2"><span>•</span> Slack Webhook Listener Architecture</li>
                <li className="flex items-start gap-2"><span>•</span> Vector Database (pgvector) Setup</li>
                <li className="flex items-start gap-2"><span>•</span> Secure Payment Backend</li>
              </ul>
            </div>
          </div>

          <div className="mt-16 pt-8 border-t border-brand-deep/5 text-center">
            <p className="text-brand-deep/40 text-sm font-medium tracking-wide">
              PROPRIETARY SENTINEL-AI ARCHITECTURE • 2026
            </p>
          </div>
        </div>
      </div>

      <div className="h-20 shrink-0" />
    </div>
  );
}
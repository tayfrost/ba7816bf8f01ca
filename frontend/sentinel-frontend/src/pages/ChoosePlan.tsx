import { useNavigate } from "react-router-dom";
import Stepper from "../components/Stepper";
import SubscriptionCard from "../components/SubscriptionCard";
import LandingHeader from "../components/LandingHeader";
import { useOnboarding } from "../state/onboarding";

export default function ChoosePlan() {
  const navigate = useNavigate();
  const { setPlan } = useOnboarding();

function selectPlan(plan: "free" | "paid") {
    setPlan(plan);
    
    navigate(`/signup?plan=${plan}`);
  }

  return (
    <div className="h-screen flex flex-col justify-around bg-transparent font-sans py-8 overflow-hidden">
      <LandingHeader />


      <div className="flex flex-col items-center mt-18">
        <img 
          src="/logo-icon.png" 
          alt="SentinelAI Logo" 
          className="h-24 md:h-40 w-auto mb-6" 
        />
        <img 
          src="/logo-text.png" 
          alt="SentinelAI" 
          className="h-8 md:h-18 w-auto opacity-90" 
        />
        
        <div className="mt-10">
          <Stepper currentPath="/plan" />
        </div>
      </div>


      <div className="max-w-7xl mx-auto px-6 w-full">
        <div className="flex flex-wrap justify-center gap-6 md:gap-8 scale-95 md:scale-100 origin-center">
          
          <div onClick={() => selectPlan("free")} className="w-full max-w-[320px] cursor-pointer">
            <SubscriptionCard 
              title="Free" 
              price="$0" 
              period="" 
              features={["Standard Alerts", "7-Day History", "Basic Support"]}
            />
          </div>

          <div onClick={() => selectPlan("paid")} className="w-full max-w-[320px] cursor-pointer">
            <SubscriptionCard 
              title="Monthly" 
              price="$29" 
              period="mo" 
              features={["AI Analysis", "Unlimited History", "Priority Support"]}
            />
          </div>

          <div onClick={() => selectPlan("paid")} className="w-full max-w-[320px] cursor-pointer">
            <SubscriptionCard 
              title="Annual" 
              price="$249" 
              period="yr" 
              features={["Everything in Monthly", "2 Months Free", "Network Audit"]}
            />
          </div>

        </div>
      </div>

      <div className="h-4" />
    </div>
  );
}
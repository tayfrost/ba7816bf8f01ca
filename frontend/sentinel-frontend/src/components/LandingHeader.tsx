import { useNavigate } from "react-router-dom";
import Button from "./Button";
import { useOnboarding } from "../state/onboarding";

interface LandingHeaderProps {
  isLoggedIn?: boolean;
}

export default function LandingHeader({ isLoggedIn = false }: LandingHeaderProps) {
  const navigate = useNavigate();
  const { signup } = useOnboarding();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/10 backdrop-blur-md border-b border-white/20">
      <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        <div className="flex items-center gap-10">
          <div 
            className="flex items-center cursor-pointer hover:opacity-80 transition-opacity gap-4"
            onClick={() => navigate("/")}
          >
            <img src="/logo-icon.png" alt="Sentinel Icon" className="w-16 h-auto" />
            
            {isLoggedIn && (
              <span style={{ 
                color: "var(--color-brand-deep)", 
                opacity: 0.8, 
                fontWeight: "900", 
                fontSize: "14px", 
                letterSpacing: "2px",
                textTransform: "uppercase" 
              }}>
                {signup?.companyName || "Sentinel AI"}
              </span>
            )}
          </div>

          <div className="hidden md:flex items-center gap-8 text-brand-deep/80 font-medium">
            {!isLoggedIn && (
              <>
                <a href="#features" className="hover:text-brand-deep transition-colors">Features</a>
                <a href="#pricing" className="hover:text-brand-deep transition-colors">Pricing</a>
                <a href="#security" className="hover:text-brand-deep transition-colors">Security</a>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          {isLoggedIn ? (
            <>
              <button className="text-brand-deep font-bold px-4 hover:opacity-70 transition-opacity">
                Account
              </button>
              <div className="w-32">
                <Button variant="primary" onClick={() => navigate("/dashboard")}>Dashboard</Button>
              </div>
            </>
          ) : (
            <>
              <button className="text-brand-deep font-bold px-4 hover:opacity-70 transition-opacity" onClick={() => navigate("/login")}>
                Login
              </button>
              <div className="w-32">
                <Button variant="primary" onClick={() => navigate("/signup")}>Join Now</Button>
              </div>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
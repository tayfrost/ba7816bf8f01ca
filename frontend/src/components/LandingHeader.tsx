import { useNavigate, useLocation } from "react-router-dom";
import Button from "./Button";
import { useOnboarding } from "../state/onboarding";

interface LandingHeaderProps {
  isLoggedIn?: boolean;
  theme?: 'light' | 'dark';
  onToggleTheme?: () => void;
  onLogin?: () => void;
}

export default function LandingHeader({ isLoggedIn = false, theme = 'light', onToggleTheme, onLogin }: LandingHeaderProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { signup } = useOnboarding();
  const isDark = theme === 'dark';

  const showToggle = isLoggedIn && (location.pathname === '/usage' || location.pathname === '/connect-accounts');

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/10 backdrop-blur-md border-b border-white/20">
      <div className="max-w-7xl mx-auto px-4 md:px-6 h-20 flex items-center justify-between gap-2">
        <div className="flex items-center gap-10">
          <div className="flex items-center cursor-pointer gap-4 shrink-0 min-w-0" onClick={() => navigate("/")}>
            <img
              src="/logo-icon.png"
              alt="Sentinel Icon"
              className="w-10 h-auto object-contain"
              onLoad={() => console.log("[logo] logo-icon.png loaded ok")}
              onError={(e) => console.error("[logo] logo-icon.png FAILED to load", (e.target as HTMLImageElement).src)}
            />
            
            {isLoggedIn && (
              <span style={{ 
                color: "var(--dynamic-text)", 
                fontWeight: "800", 
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
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 md:gap-4 shrink-0">
          {showToggle && (
            <button 
              onClick={onToggleTheme}
              style={{ color: "var(--dynamic-text)" }}
              className="hidden sm:block text-[11px] md:text-[13px] cursor-pointer font-black tracking-widest transition-all mr-2 md:mr-4"
            >
              {isDark ? "DARK MODE" : "LIGHT MODE"}
            </button>
          )}

          {isLoggedIn ? (
            <>
              <div className="w-32">
                <Button variant="primary" onClick={() => navigate("/dashboard")}>Dashboard</Button>
              </div>
            </>
          ) : (
            <>
              <button className="text-brand-deep font-bold px-4 hover:opacity-70 transition-opacity" onClick={onLogin ?? (() => navigate("/login"))}>
                Login
              </button>
              <div className="w-32">
                <Button variant="primary" onClick={() => { window.location.href = "https://sentinelai.work/signup?plan=free"; }}>Join Now</Button>
              </div>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
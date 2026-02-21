import { useNavigate } from "react-router-dom";
import Button from "./Button";

interface LandingHeaderProps {
  isLoggedIn?: boolean;
}

export default function LandingHeader({ isLoggedIn = false }: LandingHeaderProps) {
  const navigate = useNavigate();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/10 backdrop-blur-md border-b border-white/20">
      <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        <div className="flex items-center gap-10">

          <div className="hidden md:flex items-center gap-8 text-brand-deep/80 font-medium">
            {isLoggedIn ? (
              <div 
            className="flex flex-col items-center cursor-pointer hover:opacity-80 transition-opacity"
            onClick={() => navigate("/")}
          >
            <img src="/logo-icon.png" alt="Sentinel Icon" className="w-22 h-auto" />
          </div>
            
            ) : (
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
                <Button variant="primary">Dashboard</Button>
              </div>
            </>
          ) : (
            <>
              <button className="text-brand-deep font-bold px-4 hover:opacity-70 transition-opacity">
                Login
              </button>
              <div className="w-32">
                <Button variant="primary">Join Now</Button>
              </div>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
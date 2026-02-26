import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Input from "../components/Input";
import Button from "../components/Button";
import AuthCard from "../components/AuthCard";

export default function Login() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function handleLogin() {
    if (!email || !password) return;
    
    // Logic for authentication will go here
    console.log("Logging in with:", email);
    

    navigate("/usage");
  }

  return (
    <div className="min-h-screen pb-20 bg-transparent font-sans">

      <div className="flex flex-col items-center mt-24 mb-12">
        <img
          src="/logo-icon.png"
          alt="SentinelAI Logo"
          className="h-32 md:h-42 w-auto mb-6 drop-shadow-2xl"
        />
        <img
          src="/logo-text.png"
          alt="SentinelAI"
          className="h-10 md:h-14 w-auto opacity-90"
        />
      </div>

      <AuthCard>
        <div className="space-y-6">
 
          <div className="text-center mb-8">
            <h2 className="text-3xl font-serif font-black text-brand-deep leading-tight">
              Welcome Back
            </h2>
            <p className="text-xs uppercase tracking-[0.2em] text-brand-deep/50 font-bold mt-2">
              Wellness | Protection | Support
            </p>
          </div>

          <Input
            label="Admin Email"
            type="email"
            placeholder="admin@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <Input
            label="Password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <div className="pt-4 space-y-6">
            <Button variant="primary" onClick={handleLogin}>
              Log In
            </Button>


            <div className="text-center pt-2 border-t border-brand-deep/5">
              <p className="text-sm text-brand-deep/60">
                Don't have an account?{" "}
                <button 
                  onClick={() => navigate("/plan")}
                  className="text-brand-deep font-bold hover:underline underline-offset-4"
                >
                  Get Started
                </button>
              </p>
            </div>
          </div>
        </div>
      </AuthCard>
    </div>
  );
}
import React from "react";
import { useNavigate } from "react-router-dom";
import Stepper from "../components/Stepper";
import AuthCard from "../components/AuthCard"; 
import Input from "../components/Input";
import Button from "../components/Button";
import LandingHeader from "../components/LandingHeader";
import { useOnboarding } from "../state/onboarding";

export default function Payment() {
  const navigate = useNavigate();
  const { setPaymentSuccess } = useOnboarding();

  function handlePay() {
    setPaymentSuccess(true);
    navigate("/usage");
  }

  return (
    <div className="min-h-screen flex flex-col bg-transparent font-sans overflow-y-auto">
      <LandingHeader />

      <div className="flex flex-col items-center mt-16 mb-12 shrink-0">
        <div className="mb-8 mt-12">
          <Stepper currentPath="/payment" />
        </div>
        
        <AuthCard>
          <div className="text-center mb-8">
            <h1 className="text-3xl font-serif font-black text-brand-deep leading-tight">
              Secure Payment
            </h1>
            <p className="text-brand-deep/60 mt-2">
              Enter your corporate card details to continue.
            </p>
          </div>

          <form onSubmit={handlePay} className="space-y-6">
            <Input 
              label="Cardholder Name" 
              placeholder="e.g. Purpl Corp Admin" 
              required 
            />
            
            <Input 
              label="Card Number" 
              placeholder="0000 0000 0000 0000" 
              maxLength={19}
              required 
            />

            <div className="grid grid-cols-2 gap-4">
              <Input 
                label="Expiry Date" 
                placeholder="MM/YY" 
                required 
              />
              <Input 
                label="CVC" 
                placeholder="123" 
                type="password" 
                maxLength={3}
                required 
              />
            </div>

            <div className="pt-4">
              <Button type="submit" variant="primary">
                Confirm & Activate Plan
              </Button>
            </div>
          </form>

          <p className="text-center text-[10px] text-brand-deep/40 uppercase tracking-[0.2em] font-bold mt-8">
            Encrypted & Secure 256-bit SSL
          </p>
        </AuthCard>
      </div>
    </div>
  );
}
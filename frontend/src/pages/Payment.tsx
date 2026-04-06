import React, { useState } from "react";
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
  const [errors, setErrors] = useState<Record<string, string>>({});

  function handlePay(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    
    const formData = new FormData(e.currentTarget);
    const cardNum = (formData.get("cardNumber") as string || "").replace(/\s/g, "");
    const expiry = formData.get("expiryDate") as string || "";
    const cvc = formData.get("cvcCode") as string || "";
    const newErrors: Record<string, string> = {};

    if (!/^\d{16,19}$/.test(cardNum)) newErrors.card = "Card must be 16-19 digits";
    if (!/^(0[1-9]|1[0-2])\/\d{2}$/.test(expiry)) newErrors.expiry = "Use MM/YY (01-12)";
    if (!/^\d{3,4}$/.test(cvc)) newErrors.cvc = "CVC must be 3-4 digits";

    if (Object.keys(newErrors).length > 0) return setErrors(newErrors);

    setPaymentSuccess(true);
    navigate("/dashboard");
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
            
            <div>
              <Input 
                name="cardNumber" 
                label="Card Number" 
                placeholder="0000 0000 0000 0000" 
                maxLength={19}
                required 
              />
              {errors.card && <p className="text-red-500 text-[10px] font-bold mt-1 uppercase">{errors.card}</p>}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Input 
                  name="expiryDate"
                  label="Expiry Date" 
                  placeholder="MM/YY" 
                  required 
                />
                {errors.expiry && <p className="text-red-500 text-[10px] font-bold mt-1 uppercase">{errors.expiry}</p>}
              </div>
              <div>
                <Input 
                  name="cvcCode"
                  label="CVC" 
                  placeholder="123" 
                  type="password" 
                  maxLength={4}
                  required 
                />
                {errors.cvc && <p className="text-red-500 text-[10px] font-bold mt-1 uppercase">{errors.cvc}</p>}
              </div>
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
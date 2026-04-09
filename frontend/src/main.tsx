import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { OnboardingProvider } from "./state/onboarding";
import App from "./App";
import "./index.css";

if (import.meta.env.DEV) {
  console.log("[sentinel] boot — env:", {
    API_BASE_URL: import.meta.env.VITE_API_BASE_URL ?? "(unset)",
    PAYMENTS_URL: import.meta.env.VITE_PAYMENTS_URL ?? "(unset)",
    MODE: import.meta.env.MODE,
  });
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <OnboardingProvider>
        <App />
      </OnboardingProvider>
    </BrowserRouter>
  </React.StrictMode>
);

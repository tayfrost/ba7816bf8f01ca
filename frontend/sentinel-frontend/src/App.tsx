import { Navigate, Route, Routes } from "react-router-dom";
import Signup from "./pages/Signup";
import Login from "./pages/Login";
import ChoosePlan from "./pages/ChoosePlan";
import Payment from "./pages/Payment";
import Usage from "./pages/Usage";
import Dashboard from "./pages/Dashboard";
import ConnectAccounts from "./pages/ConnectAccounts";
import RequireOnboarding from "./guards/RequireOnboarding";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/plan" replace />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/plan" element={<ChoosePlan />} />
      <Route path="/payment" element={<Payment />} />

      <Route
        path="/connect-accounts"
        element={
          <RequireOnboarding>
            <ConnectAccounts />
          </RequireOnboarding>
        }
      />

      <Route
        path="/dashboard"
        element={
          <RequireOnboarding>
            <Dashboard />
          </RequireOnboarding>
        }
      />

      <Route
        path="/usage"
        element={
          <RequireOnboarding>
            <Usage />
          </RequireOnboarding>
        }
      />

      <Route path="*" element={<Navigate to="/plan" replace />} />
    </Routes>
  );
}
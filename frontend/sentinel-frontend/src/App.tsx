import { Navigate, Route, Routes } from "react-router-dom";
import Signup from "./pages/Signup";
import Login from "./pages/Login";
import ChoosePlan from "./pages/ChoosePlan";
import Payment from "./pages/Payment";
import Usage from "./pages/Usage";
import Dashboard from "./pages/Dashboard";
import ConnectAccounts from "./pages/ConnectAccounts";
import RequireOnboarding from "./guards/RequireOnboarding";
import Employees from "./pages/Employees";
import Settings from "./pages/Settings";
import EmployeeProfile from "./pages/EmployeeProfile";
import RequireAuth from "./guards/RequireAuth";
import { useThemeToggle } from "./hooks/useThemeToggle";

export default function App() {

  useThemeToggle();

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
          //<RequireAuth>
          //  <RequireOnboarding>
              <ConnectAccounts />
          //  </RequireOnboarding>
          //</RequireAuth>
        }
      />

      <Route
        path="/dashboard"
        element={
          //<RequireAuth>
            //<RequireOnboarding>
              <Dashboard />
            //</Routes></RequireOnboarding>
          //</RequireAuth>
        }
      />

      <Route
        path="/employees"
        element={
          //<RequireAuth>
            //<RequireOnboarding>
              <Employees />
            //</Routes></RequireOnboarding>
          //</RequireAuth>
        }
      />

      <Route
        path="/employees/:employeeId"
        element={
          //<RequireAuth>
            //<RequireOnboarding>
              <EmployeeProfile />
            //</Routes></RequireOnboarding>
          //</RequireAuth>
        }
      />
      
      <Route
        path="/settings"
        element={
          //<RequireAuth>
            //<RequireOnboarding>
              <Settings />
            //</Routes></RequireOnboarding>
          //</RequireAuth>
      }
    />

      <Route
        path="/usage"
        element={
          //<RequireAuth>
            //<RequireOnboarding>
              <Usage />
            //</Routes></RequireOnboarding>
          //</RequireAuth>
        }
      />

      <Route path="*" element={<Navigate to="/plan" replace />} />
    </Routes>
  );
}
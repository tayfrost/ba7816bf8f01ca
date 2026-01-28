import { Navigate, Route, Routes } from "react-router-dom";
import Signup from "./pages/Signup";
import ChoosePlan from "./pages/ChoosePlan";
import Payment from "./pages/Payment";
import Usage from "./pages/Usage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/signup" replace />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/plan" element={<ChoosePlan />} />
      <Route path="/payment" element={<Payment />} />
      <Route path="/usage" element={<Usage />} />
      <Route path="*" element={<Navigate to="/signup" replace />} />
    </Routes>
  );
}

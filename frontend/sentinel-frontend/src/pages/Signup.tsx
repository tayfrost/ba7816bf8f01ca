import Stepper from "../components/Stepper";

export default function Signup() {
  return (
    <div>
      <Stepper currentPath="/signup" />
      <div style={{ padding: 24 }}>
        <h1>Sign up</h1>
        <p>Create a company/admin account.</p>
      </div>
    </div>
  );
}

import Stepper from "../components/Stepper";

export default function Usage() {
  return (
    <div>
      <Stepper currentPath="/usage" />
      <div style={{ padding: 24 }}>
        <h1>Usage</h1>
        <p>Basic usage information / next steps.</p>
      </div>
    </div>
  );
}

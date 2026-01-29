type Step = {
  label: string;
  path: string;
};

const STEPS: Step[] = [
  { label: "Sign up", path: "/signup" },
  { label: "Plan", path: "/plan" },
  { label: "Payment", path: "/payment" },
  { label: "Usage", path: "/usage" },
];

export default function Stepper({ currentPath }: { currentPath: string }) {
  const currentIndex = STEPS.findIndex((s) => s.path === currentPath);

  return (
    <div style={{ padding: 16, borderBottom: "1px solid #eee" }}>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        {STEPS.map((s, idx) => {
          const isActive = idx === currentIndex;
          const isDone = idx < currentIndex;

          return (
            <div
              key={s.path}
              style={{
                padding: "6px 10px",
                borderRadius: 999,
                border: "1px solid #ddd",
                background: isActive ? "#f5f5f5" : "transparent",
                opacity: isDone ? 0.7 : 1,
                fontWeight: isActive ? 600 : 400,
              }}
            >
              {idx + 1}. {s.label}
            </div>
          );
        })}
      </div>
    </div>
  );
}

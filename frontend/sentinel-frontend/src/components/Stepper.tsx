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
    <div className="flex flex-wrap justify-center gap-3 p-4">
      {STEPS.map((s, idx) => {
        const isActive = idx === currentIndex;
        const isDone = idx < currentIndex;

        return (
          <div
            key={s.path}
            style={{ 
              color: "var(--dynamic-text)",
              background: isActive ? "var(--dynamic-card)" : "transparent",
              borderColor: "var(--dynamic-border)"
            }}
            className={`
              px-5 py-2.5 rounded-full border text-[12px] font-bold uppercase tracking-wider transition-all duration-300
              ${isActive 
                ? "backdrop-blur-md shadow-lg scale-105" 
                : "opacity-40"}
              ${isDone ? "opacity-20" : ""}
            `}
          >
            <span className="opacity-50 mr-2">{idx + 1}.</span>
            {s.label}
          </div>
        );
      })}
    </div>
  );
}
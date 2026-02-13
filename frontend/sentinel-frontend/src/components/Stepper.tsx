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
            className={`
              px-5 py-2.5 rounded-full border text-[12px] font-bold uppercase tracking-wider transition-all duration-300
              ${isActive 
                ? "bg-white/40 backdrop-blur-md border-white/50 text-brand-deep shadow-lg scale-105" 
                : "bg-white/10 backdrop-blur-sm border-white/20 text-brand-deep/40"}
              ${isDone ? "opacity-60 border-brand-deep/10" : ""}
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
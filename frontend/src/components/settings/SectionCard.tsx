import type { ReactNode } from "react";

type Props = {
  title: string;
  children: ReactNode;
};

export default function SectionCard({ title, children }: Props) {
  return (
    <section
      style={{
        background: "rgba(255,255,255,0.03)",
        padding: "40px",
        borderRadius: "35px",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <h3
        style={{
          fontSize: "14px",
          fontWeight: "900",
          color: "var(--color-top)",
          letterSpacing: "2px",
          textTransform: "uppercase",
          marginBottom: "30px",
        }}
      >
        {title}
      </h3>

      {children}
    </section>
  );
}
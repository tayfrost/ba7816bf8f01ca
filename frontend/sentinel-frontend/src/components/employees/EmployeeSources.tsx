type Props = {
  sources: ("slack" | "gmail" | "outlook")[];
};

const SOURCE_COLORS = {
  slack: "#7c3aed",
  gmail: "#ea4335",
  outlook: "#2563eb",
};

export default function EmployeeSources({ sources }: Props) {
  return (
    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
      {sources.map((source) => (
        <span
          key={source}
          style={{
            padding: "6px 10px",
            borderRadius: "999px",
            fontSize: "10px",
            fontWeight: 900,
            letterSpacing: "1px",
            textTransform: "uppercase",
            color: SOURCE_COLORS[source],
            background: `${SOURCE_COLORS[source]}22`,
            border: `1px solid ${SOURCE_COLORS[source]}55`,
          }}
        >
          {source}
        </span>
      ))}
    </div>
  );
}
export default function EmptyEmployees() {
  return (
    <div
      style={{
        textAlign: "center",
        padding: "100px 20px",
        opacity: 0.4,
      }}
    >
      <h2
        style={{
          fontWeight: 900,
          letterSpacing: "2px",
        }}
      >
        NO EMPLOYEES FOUND
      </h2>

      <p style={{ marginTop: "10px" }}>
        Try adjusting your filters or search query.
      </p>
    </div>
  )
}
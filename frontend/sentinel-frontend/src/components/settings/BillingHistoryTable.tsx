import type { BillingInvoice } from "../../state/settingsMock";

type Props = {
  invoices: BillingInvoice[];
};

export default function BillingHistoryTable({ invoices }: Props) {
  return (
    <div style={{ marginTop: "24px" }}>
      <div
        style={{
          fontSize: "11px",
          fontWeight: 900,
          letterSpacing: "1px",
          textTransform: "uppercase",
          opacity: 0.45,
          marginBottom: "14px",
        }}
      >
        Recent invoices
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {invoices.map((invoice) => (
          <div
            key={invoice.id}
            style={{
              display: "grid",
              gridTemplateColumns: "1.3fr 1fr 0.8fr 0.8fr",
              gap: "12px",
              alignItems: "center",
              padding: "14px 16px",
              borderRadius: "16px",
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.06)",
              fontSize: "13px",
            }}
          >
            <span style={{ fontWeight: 800 }}>{invoice.id}</span>
            <span style={{ opacity: 0.6 }}>{invoice.date}</span>
            <span>{invoice.amount}</span>
            <span style={{ color: invoice.status === "paid" ? "#2ecc71" : "#ffb347", fontWeight: 800 }}>
              {invoice.status.toUpperCase()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
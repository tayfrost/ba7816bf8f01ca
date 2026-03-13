import type { PaymentCard } from "../../state/settingsMock";

type Props = {
  cards: PaymentCard[];
};

export default function PaymentMethodsList({ cards }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px", marginBottom: "20px" }}>
      {cards.map((card) => (
        <div
          key={card.id}
          style={{
            background: "rgba(255,255,255,0.05)",
            padding: "20px 25px",
            borderRadius: "20px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            border: card.isDefault ? "1px solid var(--color-top)" : "1px solid transparent",
          }}
        >
          <div>
            <p style={{ margin: 0, fontSize: "14px", fontWeight: "800" }}>
              {card.brand.toUpperCase()} ending in {card.lastFour}
            </p>
            <p style={{ margin: 0, fontSize: "11px", opacity: 0.5 }}>{card.name}</p>
          </div>

          {card.isDefault && (
            <span style={{ fontSize: "10px", fontWeight: "900", color: "var(--color-top)" }}>
              DEFAULT
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
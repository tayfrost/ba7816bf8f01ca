export type PaymentCard = {
  id: number;
  name: string;
  lastFour: string;
  brand: "visa" | "mastercard";
  isDefault: boolean;
};

export type BillingInvoice = {
  id: string;
  date: string;
  amount: string;
  status: "paid" | "pending";
};

export const MOCK_CARDS: PaymentCard[] = [
  { id: 1, name: "J. DOE (CORPORATE)", lastFour: "4242", brand: "visa", isDefault: true },
  { id: 2, name: "SENTINEL ADMIN", lastFour: "8891", brand: "mastercard", isDefault: false },
];

export const MOCK_INVOICES: BillingInvoice[] = [
  { id: "INV-2026-001", date: "2026-03-01", amount: "$29.00", status: "paid" },
  { id: "INV-2026-000", date: "2026-02-01", amount: "$29.00", status: "paid" },
  { id: "INV-2026-999", date: "2026-01-01", amount: "$29.00", status: "paid" },
];
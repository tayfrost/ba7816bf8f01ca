type Props = {
  label: string;
  active?: boolean;
  onClick?: () => void;
};

const BRAND_ORANGE = "var(--color-top)";

export default function SidebarLink({ label, active = false, onClick }: Props) {
  return (
    <div
      onClick={onClick}
      style={{
        padding: "12px 20px",
        margin: "8px 0",
        borderRadius: "12px",
        cursor: "pointer",
        background: active ? `rgba(227, 141, 38, 0.25)` : "transparent",
        color: active ? BRAND_ORANGE : "#ffffffa0",
        fontWeight: "800",
        fontSize: "13px",
        letterSpacing: "1px",
        transition: "all 0.3s ease",
        borderLeft: active ? `4px solid ${BRAND_ORANGE}` : "4px solid transparent",
      }}
    >
      {label.toUpperCase()}
    </div>
  );
}
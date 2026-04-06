import { NavLink } from "react-router-dom";

type Props = {
  to: string;
  label: string;
  end?: boolean;
};

const BRAND_ORANGE = "var(--color-top)";

export default function SidebarLink({ to, label, end }: Props) {
  return (
    <NavLink
      to={to}
      end={end}
      style={({ isActive }) => ({
        padding: "12px 20px",
        margin: "8px 0",
        borderRadius: "12px",
        cursor: "pointer",
        background: isActive ? `rgba(227, 141, 38, 0.25)` : "transparent",
        color: isActive ? BRAND_ORANGE : "#ffffffa0",
        fontWeight: 800,
        fontSize: "13px",
        letterSpacing: "1px",
        transition: "all 0.3s ease",
        borderLeft: isActive ? `4px solid ${BRAND_ORANGE}` : "4px solid transparent",
        textDecoration: "none",
        display: "block",
      })}
    >
      {label.toUpperCase()}
    </NavLink>
  );
}
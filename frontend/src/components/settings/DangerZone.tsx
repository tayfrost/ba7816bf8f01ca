import Button from "../Button";
import { deleteMyCompany } from "../../api/companies";

export default function DangerZone() {
  const handleDelete = async () => {
    await deleteMyCompany();
    window.location.href = "/";
  };

  return (
    <div
      style={{
        border: "1px solid rgba(255,80,80,0.4)",
        borderRadius: "20px",
        padding: "28px",
        background: "rgba(255,0,0,0.05)",
        marginTop: "30px",
      }}
    >
      <h3 style={{ margin: "0 0 12px 0", color: "#ff7a7a" }}>Danger Zone</h3>

      <p style={{ fontSize: "13px", opacity: 0.7 }}>
        Deleting your workspace will permanently remove all analytics data and
        connected integrations.
      </p>

      <Button
        variant="secondary"
        className="!bg-red-500/20 !text-red-300 hover:!bg-red-500/30 border-red-400/40"
        style={{ marginTop: "12px" }}
        onClick={handleDelete}
      >
        Delete Workspace
      </Button>
    </div>
  );
}
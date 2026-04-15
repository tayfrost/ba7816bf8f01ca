import Button from "../../Button";

type Props = {
  provider: "slack" | "gmail";
  connected: boolean;
  connectedAt?: string;
  onConnect: () => void;
  onDisconnect: () => void;
};

function providerName(p: Props["provider"]) {
  if (p === "slack") return "Slack";
  return "Gmail";
}

export default function IntegrationCard({
  provider,
  connected,
  connectedAt,
  onConnect,
  onDisconnect,
}: Props) {
  return (
    <div
      style={{
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "22px",
        padding: "20px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}
    >
      <div>
        <div style={{ fontWeight: 800 }}>{providerName(provider)}</div>

        <div style={{ fontSize: "12px", opacity: 0.6 }}>
          {connected
            ? `Connected ${connectedAt ? new Date(connectedAt).toLocaleDateString() : ""}`
            : "Not connected"}
        </div>
      </div>

      {connected ? (
        <Button
          variant="secondary"
          className="!text-white !bg-red-500/20 hover:!bg-red-500/30"
          onClick={onDisconnect}
        >
          Disconnect
        </Button>
      ) : (
        <Button
          variant="secondary"
          className="!text-white !bg-white/20 hover:!bg-white/30"
          onClick={onConnect}
        >
          Connect
        </Button>
      )}
    </div>
  );
}
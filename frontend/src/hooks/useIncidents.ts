import { useEffect, useState } from "react";
import { getIncidents, getIncidentStats } from "../api";
import type { Incident, IncidentStats } from "../api";
import { dashboardDebug, dashboardDebugError } from "../utils/dashboardDebug";

type Status = "idle" | "loading" | "success" | "error";

export function useIncidents() {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [stats, setStats] = useState<IncidentStats | null>(null);

  useEffect(() => {
    let cancelled = false;
    dashboardDebug("useIncidents", "effect-start", { pollIntervalMs: 30000 });

    async function load() {
      setStatus("loading");
      setError(null);
      dashboardDebug("useIncidents", "fetch-start", { limit: 10, skip: 0 });

      try {
        const [incidentData, statsData] = await Promise.all([
          getIncidents(0, 10),
          getIncidentStats(),
        ]);

        if (cancelled) return;

        setIncidents(incidentData);
        setStats(statsData);
        setStatus("success");
        dashboardDebug("useIncidents", "fetch-success", {
          incidentsCount: incidentData.length,
          stats: statsData,
          firstIncident: incidentData[0]
            ? {
                incident_id: incidentData[0].incident_id,
                reason: incidentData[0].class_reason,
                created_at: incidentData[0].created_at,
                user: incidentData[0].slack_user_id,
              }
            : null,
        });
      } catch (err) {
        if (cancelled) return;
        console.error(err);
        dashboardDebugError("useIncidents", "fetch-failed", err);
        setStatus("error");
        setError("Failed to load incidents.");
        dashboardDebug("useIncidents", "state-error", { error: "Failed to load incidents." });
      }
    }

    load();

    const interval = setInterval(load, 30_000);

    return () => {
      cancelled = true;
      clearInterval(interval);
      dashboardDebug("useIncidents", "effect-cleanup");
    };
  }, []);

  return { status, error, incidents, stats };
}
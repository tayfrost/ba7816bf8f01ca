import { useEffect, useState } from "react";
import { getIncidents, getIncidentStats } from "../api";
import type { Incident, IncidentStats } from "../api";

type Status = "idle" | "loading" | "success" | "error";

export function useIncidents() {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [stats, setStats] = useState<IncidentStats | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setStatus("loading");
      setError(null);

      try {
        const [incidentData, statsData] = await Promise.all([
          getIncidents(0, 10),
          getIncidentStats(),
        ]);

        if (cancelled) return;

        setIncidents(incidentData);
        setStats(statsData);
        setStatus("success");
      } catch (err) {
        if (cancelled) return;
        console.error(err);
        setStatus("error");
        setError("Failed to load incidents.");
      }
    }

    load();

    const interval = setInterval(load, 30_000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return { status, error, incidents, stats };
}
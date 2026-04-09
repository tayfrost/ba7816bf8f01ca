import { useEffect, useState } from "react";
import { getMe } from "../api";
import { ApiError } from "../api/client";

type Status = "idle" | "loading" | "success" | "error";

export function useCurrentUser() {
  const [status, setStatus] = useState<Status>("idle");
  const [user, setUser] = useState<Awaited<ReturnType<typeof getMe>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("sentinel_access_token");
    if (!token) {
      setStatus("error");
      setError("No token found.");
      return;
    }

    let cancelled = false;

    async function run() {
      setStatus("loading");
      setError(null);

      try {
        const me = await getMe();
        if (cancelled) return;

        setUser(me);
        setStatus("success");
      } catch (err) {
        if (cancelled) return;

        // Only clear the token on a genuine 401 — not on network errors or 5xx
        if (err instanceof ApiError && err.status === 401) {
          localStorage.removeItem("sentinel_access_token");
        }
        setUser(null);
        setStatus("error");
        setError("Session expired or invalid.");
        console.error(err);
      }
    }

    run();

    return () => {
      cancelled = true;
    };
  }, []);

  return { status, user, error };
}
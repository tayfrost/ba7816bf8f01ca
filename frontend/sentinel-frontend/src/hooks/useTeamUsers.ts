import { useEffect, useState } from "react";
import { getUsers, updateUserRole, deactivateUser } from "../api";
import type { UserResponse } from "../api";

type Status = "idle" | "loading" | "success" | "error";

export function useTeamUsers() {
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setStatus("loading");

      try {
        const data = await getUsers();

        if (cancelled) return;

        setUsers(data);
        setStatus("success");
      } catch (err) {
        console.error(err);
        if (cancelled) return;

        setStatus("error");
        setError("Failed to load team members.");
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, []);

  async function changeRole(userId: number, role: "admin" | "biller" | "viewer") {
    await updateUserRole(userId, role);

    setUsers((prev) =>
      prev.map((u) =>
        u.user_id === userId ? { ...u, role } : u
      )
    );
  }

  async function removeUser(userId: number) {
    await deactivateUser(userId);

    setUsers((prev) =>
      prev.filter((u) => u.user_id !== userId)
    );
  }

  return {
    users,
    status,
    error,
    changeRole,
    removeUser,
  };
}
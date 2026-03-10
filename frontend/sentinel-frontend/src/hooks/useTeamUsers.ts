import { useEffect, useState } from "react";
import type { UserResponse } from "../api";
import { getUsers, updateUserRole, deactivateUser, inviteUser } from "../api";

type Status = "idle" | "loading" | "success" | "error";

export function useTeamUsers() {
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [busyUserId, setBusyUserId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setStatus("loading");
      setError(null);

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
    setBusyUserId(userId);
    setError(null);

    try {
      await updateUserRole(userId, role);

      setUsers((prev) =>
        prev.map((u) => (u.user_id === userId ? { ...u, role } : u))
      );
    } catch (err) {
      console.error(err);
      setError("Failed to update user role.");
    } finally {
      setBusyUserId(null);
    }
  }

  async function removeUser(userId: number) {
    setBusyUserId(userId);
    setError(null);

    try {
      await deactivateUser(userId);
      setUsers((prev) => prev.filter((u) => u.user_id !== userId));
    } catch (err) {
      console.error(err);
      setError("Failed to deactivate user.");
    } finally {
      setBusyUserId(null);
    }
  }

  async function invite(params: {
    email: string;
    name: string;
    surname: string;
    role: "admin" | "biller" | "viewer";
  }) {
    setBusyUserId(-1);
    setError(null);

    try {
      const created = await inviteUser(params);
      setUsers((prev) => [...prev, created]);
    } catch (err) {
      console.error(err);
      setError("Failed to invite user.");
    } finally {
      setBusyUserId(null);
    }
  }

  return {
    users,
    status,
    error,
    busyUserId,
    changeRole,
    removeUser,
    invite,
  };
}
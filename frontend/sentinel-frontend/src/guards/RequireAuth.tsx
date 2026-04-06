import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useCurrentUser } from "../hooks/useCurrentUser";

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const { status, user } = useCurrentUser();
  const location = useLocation();

  const token = localStorage.getItem("sentinel_access_token");

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (status === "loading" || status === "idle") {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          background: "linear-gradient(to bottom, #20022bfd, #1a011d)",
          color: "white",
          fontFamily: "'Outfit', 'Inter', sans-serif",
        }}
      >
        Checking session...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
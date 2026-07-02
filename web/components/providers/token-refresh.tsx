"use client";

import { useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function refreshAccessToken(): Promise<boolean> {
  const res = await fetch(`${API_BASE}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: "" }),
    credentials: "include",
  });
  return res.ok;
}

/**
 * Attempts token refresh on mount when session may be stale.
 * Server-side refresh is handled via httpOnly refresh_token cookie in a future
 * dedicated route; this client stub re-validates on focus.
 */
export function TokenRefreshProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const onFocus = () => {
      void refreshAccessToken();
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  return <>{children}</>;
}

"use client";

import { useEffect, useRef } from "react";

import {
  getClientRefreshToken,
  setAuthTokens,
  clearAuthTokens,
} from "@/lib/auth/client-session";

// Don't hammer the refresh route on every focus event.
const MIN_REFRESH_INTERVAL_MS = 5 * 60 * 1000;

/**
 * Rotates the session on window focus via the FastAPI refresh endpoint.
 */
export function TokenRefreshProvider({ children }: { children: React.ReactNode }) {
  const lastAttempt = useRef(0);

  useEffect(() => {
    const onFocus = async () => {
      const now = Date.now();
      if (now - lastAttempt.current < MIN_REFRESH_INTERVAL_MS) return;
      lastAttempt.current = now;
      const refreshToken = getClientRefreshToken();
      if (!refreshToken) return;
      try {
        const res = await fetch("/api/auth/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
          cache: "no-store",
        });
        if (!res.ok) {
          clearAuthTokens();
          return;
        }
        const data = await res.json();
        setAuthTokens(data.access_token, data.refresh_token);
      } catch {
        /* ignore transient network errors */
      }
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  return <>{children}</>;
}

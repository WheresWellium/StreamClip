"use client";

import { useEffect, useRef } from "react";

// Don't hammer the refresh route on every focus event.
const MIN_REFRESH_INTERVAL_MS = 5 * 60 * 1000;

/**
 * Rotates the session on window focus via the BFF refresh route, which
 * exchanges the httpOnly refresh-token cookie server-side.
 */
export function TokenRefreshProvider({ children }: { children: React.ReactNode }) {
  const lastAttempt = useRef(0);

  useEffect(() => {
    const onFocus = () => {
      const now = Date.now();
      if (now - lastAttempt.current < MIN_REFRESH_INTERVAL_MS) return;
      lastAttempt.current = now;
      // 401 just means no session — nothing to do client-side.
      void fetch("/api/auth/refresh", { method: "POST" }).catch(() => {});
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  return <>{children}</>;
}

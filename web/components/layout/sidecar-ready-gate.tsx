"use client";

import { useEffect, useState } from "react";

import { metaApi } from "@/lib/api/client";

const POLL_MS = 750;
const MAX_ATTEMPTS = 120;

/**
 * Blocks the shell until the local sidecar answers /api/health.
 * Prevents unstyled or half-loaded UI when Electron opens before uvicorn is ready.
 */
export function SidecarReadyGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let tries = 0;

    const poll = async () => {
      tries += 1;
      if (!cancelled) setAttempt(tries);
      try {
        await metaApi.health();
        if (!cancelled) setReady(true);
        return;
      } catch {
        if (cancelled || tries >= MAX_ATTEMPTS) return;
        window.setTimeout(() => void poll(), POLL_MS);
      }
    };

    void poll();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) {
    return (
      <div className="min-h-screen hero-gradient flex flex-col items-center justify-center gap-4 px-6 text-center">
        <div
          className="h-8 w-8 animate-spin rounded-full border-2 border-sky-400/30 border-t-sky-400"
          aria-hidden
        />
        <div>
          <p className="font-medium text-foreground">Starting StreamClip…</p>
          <p className="text-sm text-muted-foreground mt-1">
            Waiting for the local engine
            {attempt > 1 ? ` (${attempt}/${MAX_ATTEMPTS})` : ""}
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

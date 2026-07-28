"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { LoadingScreen } from "@/components/loading";
import { createQClipBootConfig, LOADING_TIPS_DESKTOP } from "@/lib/loading";
import { metaApi } from "@/lib/api/client";

const POLL_MS = 750;
const MAX_ATTEMPTS = 120;
const FAILED_OPEN_TIPS = [
  "Engine still starting — the studio will reconnect when ready.",
] as const;

/**
 * Blocks the shell until the local sidecar answers /api/health.
 * Renders the cinematic boot loader so Electron never flashes a half-ready UI.
 * Always exits after max attempts / maxWait — users are never trapped.
 */
export function SidecarReadyGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [failedOpen, setFailedOpen] = useState(false);
  const [showLoader, setShowLoader] = useState(true);

  const markReady = useCallback((softFail = false) => {
    setReady(true);
    if (softFail) setFailedOpen(true);
  }, []);

  useEffect(() => {
    let cancelled = false;
    let tries = 0;
    let timer: number | undefined;

    const poll = async () => {
      tries += 1;
      if (!cancelled) setAttempt(tries);
      try {
        await metaApi.health();
        if (!cancelled) markReady(false);
        return;
      } catch {
        if (cancelled) return;
        if (tries >= MAX_ATTEMPTS) {
          // Soft-open the app rather than trapping on the loader forever.
          markReady(true);
          return;
        }
        timer = window.setTimeout(() => void poll(), POLL_MS);
      }
    };

    void poll();
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [markReady]);

  const onLoadingComplete = useCallback(() => {
    // Covers lifecycle maxWait firing before health/poll gives up.
    setReady(true);
  }, []);

  const onTransitionComplete = useCallback(() => {
    setShowLoader(false);
  }, []);

  const config = useMemo(
    () =>
      createQClipBootConfig({
        statusMessage: failedOpen ? "Continuing" : "Starting studio",
        tips: failedOpen ? [...FAILED_OPEN_TIPS] : LOADING_TIPS_DESKTOP,
        progressMode: "determinate",
        maxWaitMs: Math.max(90_000, POLL_MS * MAX_ATTEMPTS + 5_000),
        onLoadingComplete,
        onTransitionComplete,
      }),
    [failedOpen, onLoadingComplete, onTransitionComplete],
  );

  // Soft progress from health poll attempts (capped; lifecycle handles honesty).
  const softProgress = Math.min(
    92,
    Math.max(4, Math.round((attempt / MAX_ATTEMPTS) * 100)),
  );

  return (
    <>
      {showLoader ? (
        <LoadingScreen
          isReady={ready}
          progress={softProgress}
          config={config}
          composition="lower-left"
        />
      ) : null}
      {ready ? children : null}
    </>
  );
}

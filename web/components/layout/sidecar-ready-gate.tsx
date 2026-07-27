"use client";

import { useEffect, useMemo, useState } from "react";

import {
  LoadingScreen,
  resolveLoadingScreenConfig,
  useLoadingLifecycle,
} from "@/components/loading-screen";
import { metaApi } from "@/lib/api/client";

const POLL_MS = 750;
const MAX_ATTEMPTS = 120;

/**
 * Blocks the shell until the local sidecar answers /api/health,
 * presenting the cinematic boot loader meanwhile.
 * Falls back after max attempts / max wait so users are never trapped.
 */
export function SidecarReadyGate({ children }: { children: React.ReactNode }) {
  const [sidecarReady, setSidecarReady] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [engineUnavailable, setEngineUnavailable] = useState(false);

  const config = useMemo(
    () =>
      resolveLoadingScreenConfig({
        tips: engineUnavailable
          ? [
              "Local engine did not respond — opening studio anyway…",
              "You can retry from Settings if jobs fail to start.",
            ]
          : attempt > 1
            ? [
                `Waiting for the local engine (${attempt}/${MAX_ATTEMPTS})`,
                "Warming the local engine…",
                "Preparing clip studio…",
              ]
            : undefined,
        timing: {
          // Align hard timeout with health poll budget.
          maxWaitMs: MAX_ATTEMPTS * POLL_MS,
        },
      }),
    [attempt, engineUnavailable],
  );

  useEffect(() => {
    let cancelled = false;
    let tries = 0;
    let timer: number | undefined;

    const poll = async () => {
      tries += 1;
      if (!cancelled) setAttempt(tries);
      try {
        await metaApi.health();
        if (!cancelled) setSidecarReady(true);
        return;
      } catch {
        if (cancelled) return;
        if (tries >= MAX_ATTEMPTS) {
          setEngineUnavailable(true);
          setSidecarReady(true);
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
  }, []);

  const lifecycle = useLoadingLifecycle({
    isReady: sidecarReady,
    progressMode: "indeterminate",
    minDisplayMs: config.timing.minDisplayMs,
    entranceMs: config.timing.entranceMs,
    exitMs: config.timing.exitMs,
    maxWaitMs: config.timing.maxWaitMs,
    onLoadingComplete: config.onLoadingComplete,
    onTransitionComplete: config.onTransitionComplete,
  });

  return (
    <>
      {lifecycle.showApp ? children : null}
      {lifecycle.showLoader ? (
        <LoadingScreen
          config={config}
          phase={lifecycle.phase}
          progress={lifecycle.displayProgress}
          progressMode="indeterminate"
        />
      ) : null}
    </>
  );
}

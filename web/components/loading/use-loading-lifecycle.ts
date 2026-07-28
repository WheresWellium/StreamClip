"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  computeLoadingLifecycle,
  resolveLoadingConfig,
  type LoadingPhase,
  type LoadingScreenConfig,
  type ReducedMotionBehavior,
  type ResolvedLoadingScreenConfig,
} from "@/lib/loading";

export interface UseLoadingLifecycleOptions {
  isReady: boolean;
  progress?: number;
  config?: Partial<LoadingScreenConfig>;
}

export interface UseLoadingLifecycleResult {
  phase: LoadingPhase;
  displayProgress: number;
  visible: boolean;
  exiting: boolean;
  timedOut: boolean;
  reducedMotion: boolean;
  resolved: ResolvedLoadingScreenConfig;
  announceText: string;
}

const TICK_MS = 100;
/** Snappy exit when motion is reduced — keep CSS + lifecycle in sync. */
const REDUCED_EXIT_MS = 140;

function readPrefersReducedMotion(
  behavior: ReducedMotionBehavior,
): boolean {
  if (behavior === "force-reduced") return true;
  if (behavior === "force-full") return false;
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Owns boot → load → exit → unmount timing.
 * Safe against double-exit races and missed readiness signals (maxWaitMs).
 * Stops the tick loop once the shell unmounts (no forever timers).
 */
export function useLoadingLifecycle({
  isReady,
  progress,
  config,
}: UseLoadingLifecycleOptions): UseLoadingLifecycleResult {
  const resolved = useMemo(() => resolveLoadingConfig(config), [config]);
  const mountedAt = useRef<number | null>(null);
  const exitStartedAt = useRef<number | null>(null);
  const completedRef = useRef(false);
  const transitionedRef = useRef(false);
  const onLoadingCompleteRef = useRef(resolved.onLoadingComplete);
  const onTransitionCompleteRef = useRef(resolved.onTransitionComplete);

  onLoadingCompleteRef.current = resolved.onLoadingComplete;
  onTransitionCompleteRef.current = resolved.onTransitionComplete;

  const [reducedMotion, setReducedMotion] = useState(() =>
    readPrefersReducedMotion(resolved.reducedMotion),
  );
  const [nowMs, setNowMs] = useState(0);
  const [exitRequested, setExitRequested] = useState(false);
  const [exitElapsedMs, setExitElapsedMs] = useState(0);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const update = () =>
      setReducedMotion(readPrefersReducedMotion(resolved.reducedMotion));
    update();
    if (
      resolved.reducedMotion === "force-reduced" ||
      resolved.reducedMotion === "force-full"
    ) {
      return;
    }
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, [resolved.reducedMotion]);

  const effectiveExitMs = reducedMotion
    ? Math.min(resolved.exitMs, REDUCED_EXIT_MS)
    : resolved.exitMs;

  useEffect(() => {
    if (!visible) return;

    mountedAt.current = performance.now();
    let cancelled = false;
    let raf = 0;

    const tick = () => {
      if (cancelled || mountedAt.current == null) return;
      const elapsed = performance.now() - mountedAt.current;
      setNowMs(elapsed);
      if (exitStartedAt.current != null) {
        setExitElapsedMs(performance.now() - exitStartedAt.current);
      }
    };

    // rAF for the first paint, then a calm interval — avoids layout thrash
    // from stacking timers while still driving lifecycle honestly.
    raf = window.requestAnimationFrame(tick);
    const id = window.setInterval(tick, TICK_MS);
    return () => {
      cancelled = true;
      window.cancelAnimationFrame(raf);
      window.clearInterval(id);
    };
  }, [visible]);

  const snapshot = computeLoadingLifecycle({
    isReady,
    progress: progress ?? resolved.progress,
    minDisplayMs: resolved.minDisplayMs,
    exitMs: effectiveExitMs,
    maxWaitMs: resolved.maxWaitMs,
    progressMode: resolved.progressMode,
    nowMs,
    exitRequested,
    exitElapsedMs,
  });

  useEffect(() => {
    if (!snapshot.shouldStartExit || exitRequested) return;
    exitStartedAt.current = performance.now();
    setExitRequested(true);
    setExitElapsedMs(0);
    if (!completedRef.current) {
      completedRef.current = true;
      onLoadingCompleteRef.current?.();
    }
  }, [snapshot.shouldStartExit, exitRequested]);

  useEffect(() => {
    if (!snapshot.shouldUnmount || !visible) return;
    setVisible(false);
    if (!transitionedRef.current) {
      transitionedRef.current = true;
      onTransitionCompleteRef.current?.();
    }
  }, [snapshot.shouldUnmount, visible]);

  // Lock document scroll while the full-viewport shell is up.
  useEffect(() => {
    if (!visible || typeof document === "undefined") return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [visible]);

  const announceText = snapshot.timedOut
    ? `${resolved.title} is taking longer than expected. Continuing.`
    : isReady
      ? `${resolved.title} is ready.`
      : `${resolved.statusMessage}. ${resolved.tips[0] ?? ""}`.trim();

  return {
    phase: snapshot.phase,
    displayProgress: snapshot.displayProgress,
    visible,
    exiting: exitRequested && visible,
    timedOut: snapshot.timedOut,
    reducedMotion,
    resolved,
    announceText,
  };
}

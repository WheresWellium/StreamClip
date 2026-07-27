"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  clampProgress,
  softIndeterminateProgress,
} from "../resolve-config";
import type {
  LoadingLifecycleOptions,
  LoadingLifecycleState,
  LoadingScreenPhase,
} from "../types";

/**
 * Owns entrance → loading → exit → done transitions.
 * Combines real readiness with min-display and max-wait safeguards.
 */
export function useLoadingLifecycle(
  options: LoadingLifecycleOptions,
): LoadingLifecycleState {
  const {
    isReady,
    progress = null,
    progressMode = "indeterminate",
    minDisplayMs,
    entranceMs,
    exitMs,
    maxWaitMs,
    onLoadingComplete,
    onTransitionComplete,
  } = options;

  const [phase, setPhase] = useState<LoadingScreenPhase>("entering");
  const [elapsedMs, setElapsedMs] = useState(0);
  const [timedOut, setTimedOut] = useState(false);
  const [forceComplete, setForceComplete] = useState(false);

  const mountedAt = useRef<number>(0);
  const exitStarted = useRef(false);
  const completedNotified = useRef(false);
  const transitionNotified = useRef(false);
  const onLoadingCompleteRef = useRef(onLoadingComplete);
  const onTransitionCompleteRef = useRef(onTransitionComplete);

  useEffect(() => {
    onLoadingCompleteRef.current = onLoadingComplete;
    onTransitionCompleteRef.current = onTransitionComplete;
  }, [onLoadingComplete, onTransitionComplete]);

  useEffect(() => {
    mountedAt.current = performance.now();
    const entranceTimer = window.setTimeout(() => {
      setPhase((p) => (p === "entering" ? "loading" : p));
    }, Math.max(0, entranceMs));

    const tick = window.setInterval(() => {
      setElapsedMs(performance.now() - mountedAt.current);
    }, 100);

    return () => {
      window.clearTimeout(entranceTimer);
      window.clearInterval(tick);
    };
  }, [entranceMs]);

  useEffect(() => {
    const maxTimer = window.setTimeout(() => {
      setTimedOut(true);
      setForceComplete(true);
    }, Math.max(minDisplayMs, maxWaitMs));
    return () => window.clearTimeout(maxTimer);
  }, [maxWaitMs, minDisplayMs]);

  const beginExit = useCallback(() => {
    if (exitStarted.current) return;
    exitStarted.current = true;
    if (!completedNotified.current) {
      completedNotified.current = true;
      onLoadingCompleteRef.current?.();
    }
    setPhase("exiting");
    window.setTimeout(() => {
      setPhase("done");
      if (!transitionNotified.current) {
        transitionNotified.current = true;
        onTransitionCompleteRef.current?.();
      }
    }, Math.max(0, exitMs));
  }, [exitMs]);

  const complete = useCallback(() => {
    setForceComplete(true);
  }, []);

  useEffect(() => {
    if (phase === "exiting" || phase === "done") return;
    const ready = isReady || forceComplete;
    if (!ready) return;
    const waited = performance.now() - mountedAt.current;
    const remaining = Math.max(0, minDisplayMs - waited);
    const timer = window.setTimeout(() => beginExit(), remaining);
    return () => window.clearTimeout(timer);
  }, [isReady, forceComplete, minDisplayMs, beginExit, phase]);

  let displayProgress: number;
  if (progressMode === "determinate" && progress != null) {
    displayProgress = clampProgress(progress);
    if ((isReady || forceComplete) && displayProgress < 1) {
      displayProgress = 1;
    }
  } else {
    displayProgress = softIndeterminateProgress(
      elapsedMs,
      isReady || forceComplete,
    );
  }

  return {
    phase,
    displayProgress,
    showLoader: phase !== "done",
    showApp: phase === "exiting" || phase === "done",
    elapsedMs,
    timedOut,
    complete,
  };
}

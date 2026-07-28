import type {
  LoadingLifecycleInput,
  LoadingLifecycleResult,
  LoadingPhase,
} from "./types";

/** Soft ceiling for indeterminate visuals before real readiness. */
export const INDETERMINATE_CAP = 86;

/**
 * Map elapsed time to a calm indeterminate progress curve.
 * Asymptotic toward INDETERMINATE_CAP — never jumps to 100 alone.
 */
export function indeterminateProgress(elapsedMs: number, maxWaitMs: number): number {
  const t = Math.min(1, Math.max(0, elapsedMs / Math.max(1, maxWaitMs * 0.85)));
  // Ease-out cubic toward cap
  const eased = 1 - Math.pow(1 - t, 3);
  return Math.min(INDETERMINATE_CAP, eased * INDETERMINATE_CAP);
}

/**
 * Blend real progress with a soft floor so the bar never snaps backward.
 */
export function blendDeterminateProgress(
  reported: number,
  elapsedMs: number,
  maxWaitMs: number,
): number {
  const soft = indeterminateProgress(elapsedMs, maxWaitMs) * 0.35;
  const clamped = Math.min(100, Math.max(0, reported));
  if (!Number.isFinite(clamped)) return soft;
  return Math.min(99, Math.max(soft, clamped));
}

/**
 * Pure loading lifecycle — testable without React.
 * Prevents flicker (min display), traps (max wait), and racey double-exits.
 */
export function computeLoadingLifecycle(
  input: LoadingLifecycleInput,
): LoadingLifecycleResult {
  const {
    isReady,
    progress,
    minDisplayMs,
    exitMs,
    maxWaitMs,
    progressMode,
    nowMs,
    exitRequested,
    exitElapsedMs,
  } = input;

  const timedOut = nowMs >= maxWaitMs;
  const minElapsed = nowMs >= minDisplayMs;
  const canComplete = timedOut || (isReady && minElapsed);

  let displayProgress: number;
  if (progressMode === "determinate" && typeof progress === "number") {
    displayProgress = blendDeterminateProgress(progress, nowMs, maxWaitMs);
  } else {
    displayProgress = indeterminateProgress(nowMs, maxWaitMs);
  }

  if (canComplete || exitRequested) {
    displayProgress = 100;
  }

  let phase: LoadingPhase;
  let shouldStartExit = false;
  let shouldUnmount = false;

  if (exitRequested) {
    if (exitElapsedMs >= exitMs) {
      phase = "done";
      shouldUnmount = true;
    } else {
      phase = "exiting";
    }
  } else if (canComplete) {
    phase = "exiting";
    shouldStartExit = true;
  } else if (nowMs < 80) {
    phase = "boot";
  } else if (nowMs < minDisplayMs * 0.35) {
    phase = "entering";
  } else {
    phase = "loading";
  }

  return {
    phase,
    displayProgress,
    shouldUnmount,
    shouldStartExit,
    timedOut,
  };
}

import { DEFAULT_LOADING_SCREEN_CONFIG } from "./defaults";
import type {
  LoadingScreenConfig,
  LoadingScreenConfigInput,
} from "./types";

/**
 * Deep-merge a partial config onto defaults.
 * Keeps nested overlay/colors/timing/focal point overrides ergonomic.
 */
export function resolveLoadingScreenConfig(
  input: LoadingScreenConfigInput = {},
): LoadingScreenConfig {
  const base = DEFAULT_LOADING_SCREEN_CONFIG;
  return {
    ...base,
    ...input,
    coverFocalPoint: {
      ...base.coverFocalPoint,
      ...input.coverFocalPoint,
    },
    overlay: {
      ...base.overlay,
      ...input.overlay,
    },
    colors: {
      ...base.colors,
      ...input.colors,
    },
    timing: {
      ...base.timing,
      ...input.timing,
    },
    tips: input.tips ?? base.tips,
  };
}

/** Clamp progress into the inclusive 0–1 range. */
export function clampProgress(value: number): number {
  if (!Number.isFinite(value)) return 0;
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

/**
 * Soft asymptotic progress for unknown loads.
 * Never reports 1.0 until `isReady` — avoids fake completion.
 */
export function softIndeterminateProgress(
  elapsedMs: number,
  isReady: boolean,
): number {
  if (isReady) return 1;
  // Approach ~0.82 asymptotically over ~12s without hard jumps.
  const t = Math.max(0, elapsedMs) / 12_000;
  return clampProgress(0.82 * (1 - Math.exp(-2.2 * t)));
}

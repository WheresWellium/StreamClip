/**
 * Loading-screen configuration and lifecycle types.
 * Config-driven API — swap cover art, theme, timings without rewriting components.
 */

export type LoadingProgressMode = "determinate" | "indeterminate";

export type LoadingAnimationVariant = "cinematic" | "terminal" | "minimal";

export type ReducedMotionBehavior = "respect" | "ignore" | "force-reduced";

export type LoadingScreenPhase =
  | "entering"
  | "loading"
  | "exiting"
  | "done";

export interface LoadingScreenFocalPoint {
  /** Horizontal focus 0–100 (CSS object-position). */
  x: number;
  /** Vertical focus 0–100 (CSS object-position). */
  y: number;
}

export interface LoadingScreenOverlayConfig {
  /** HSL components without `hsl()`, e.g. `"186 42% 4%"`. */
  color: string;
  /** 0–1 overlay strength over cover art. */
  opacity: number;
  /** Extra vignette darkness 0–1. */
  vignetteIntensity: number;
}

export interface LoadingScreenColors {
  accent: string;
  progressTrack: string;
  progressFill: string;
  title: string;
  subtitle: string;
  status: string;
}

export interface LoadingScreenTiming {
  /** Prevent flicker on very fast ready signals (ms). */
  minDisplayMs: number;
  entranceMs: number;
  exitMs: number;
  /** Hard cap — never trap the user on the loader (ms). */
  maxWaitMs: number;
  /** Tip rotation interval when tips are configured (ms). */
  tipRotateMs: number;
}

export interface LoadingScreenConfig {
  title: string;
  subtitle?: string;
  /** Accessible short name announced to screen readers. */
  ariaLabel?: string;
  /** Optional brand mark (React node or image URL). */
  logoSrc?: string | null;
  showBrandMark: boolean;
  coverImageSrc: string | null;
  coverFocalPoint: LoadingScreenFocalPoint;
  /** Fallback gradient stops when cover fails or is null (CSS colors). */
  fallbackGradient: string;
  overlay: LoadingScreenOverlayConfig;
  colors: LoadingScreenColors;
  statusMessage: string;
  /** Optional rotating tips under the status line. */
  tips: string[];
  progressMode: LoadingProgressMode;
  /** 0–1 when progressMode is determinate. */
  progress: number;
  timing: LoadingScreenTiming;
  variant: LoadingAnimationVariant;
  reducedMotion: ReducedMotionBehavior;
  /** Subtle film grain layer (disabled under reduced motion). */
  enableGrain: boolean;
  composition: "center" | "lower-left";
  onLoadingComplete?: () => void;
  onTransitionComplete?: () => void;
}

/** Partial override accepted by the public API. */
export type LoadingScreenConfigInput = Partial<
  Omit<LoadingScreenConfig, "overlay" | "colors" | "timing" | "coverFocalPoint">
> & {
  overlay?: Partial<LoadingScreenOverlayConfig>;
  colors?: Partial<LoadingScreenColors>;
  timing?: Partial<LoadingScreenTiming>;
  coverFocalPoint?: Partial<LoadingScreenFocalPoint>;
};

export interface LoadingLifecycleOptions {
  /** External readiness signal (health check, route data, etc.). */
  isReady: boolean;
  /** Optional real progress 0–1; omit for indeterminate. */
  progress?: number | null;
  progressMode?: LoadingProgressMode;
  minDisplayMs: number;
  entranceMs: number;
  exitMs: number;
  maxWaitMs: number;
  onLoadingComplete?: () => void;
  onTransitionComplete?: () => void;
}

export interface LoadingLifecycleState {
  phase: LoadingScreenPhase;
  /** Display progress 0–1 (may be soft/indeterminate visual). */
  displayProgress: number;
  /** True while the loader should remain mounted. */
  showLoader: boolean;
  /** True once the app shell may mount under the exit overlay. */
  showApp: boolean;
  /** Elapsed ms since mount. */
  elapsedMs: number;
  /** Whether the max-wait fallback fired. */
  timedOut: boolean;
  /** Begin exit sequence (also called automatically when ready). */
  complete: () => void;
}

/**
 * Config-driven cinematic loading screen types.
 * Swap cover art, colors, copy, and timing without touching component logic.
 */

export type LoadingProgressMode = "determinate" | "indeterminate";

export type LoadingAnimationVariant =
  | "cinematic"
  | "minimal"
  | "terminal";

export type ReducedMotionBehavior =
  | "respect"
  | "force-full"
  | "force-reduced";

export type LoadingPhase =
  | "boot"
  | "entering"
  | "loading"
  | "exiting"
  | "done";

export interface LoadingFocalPoint {
  /** Horizontal focus 0–100 (CSS object-position / background-position). */
  x: number;
  /** Vertical focus 0–100. */
  y: number;
}

export interface LoadingScreenConfig {
  title: string;
  subtitle?: string;
  /** Optional image/SVG brand mark URL. */
  logoSrc?: string;
  /** Show the built-in geometric mark when logoSrc is absent. */
  showLogoMark?: boolean;
  /** Cover / hero background. Prefer SVG/WebP under /public/loading/. */
  coverSrc?: string;
  coverFocalPoint?: LoadingFocalPoint;
  /** CSS color for the readability overlay (e.g. "hsl(186 42% 6%)"). */
  overlayColor?: string;
  /** 0–1 overlay strength. */
  overlayOpacity?: number;
  /** Accent used for glow / mark (CSS color). */
  accentColor?: string;
  /** Progress fill color (CSS color). */
  progressColor?: string;
  /** Primary status line (e.g. "Loading"). */
  statusMessage?: string;
  /** Optional rotating tips under the status line. */
  tips?: string[];
  tipIntervalMs?: number;
  progressMode?: LoadingProgressMode;
  /** 0–100 when progressMode is determinate. */
  progress?: number;
  /** Prevent flicker on fast readiness. */
  minDisplayMs?: number;
  entranceMs?: number;
  exitMs?: number;
  /** Hard ceiling — never leave the user trapped. */
  maxWaitMs?: number;
  animationVariant?: LoadingAnimationVariant;
  reducedMotion?: ReducedMotionBehavior;
  onLoadingComplete?: () => void;
  onTransitionComplete?: () => void;
  /** Extra class on the root shell. */
  className?: string;
}

export interface ResolvedLoadingScreenConfig
  extends Required<
    Omit<
      LoadingScreenConfig,
      | "logoSrc"
      | "coverSrc"
      | "onLoadingComplete"
      | "onTransitionComplete"
      | "className"
      | "tips"
      | "subtitle"
    >
  > {
  logoSrc?: string;
  coverSrc?: string;
  subtitle?: string;
  tips: string[];
  className: string;
  onLoadingComplete?: () => void;
  onTransitionComplete?: () => void;
}

export interface LoadingLifecycleInput {
  /** External readiness signal (health, route data, fonts, etc.). */
  isReady: boolean;
  /** Optional real progress 0–100; ignored in indeterminate mode. */
  progress?: number;
  minDisplayMs: number;
  exitMs: number;
  maxWaitMs: number;
  progressMode: LoadingProgressMode;
  /** Wall-clock ms since the loader mounted (injected for tests). */
  nowMs: number;
  /** Whether an exit animation has already been requested. */
  exitRequested: boolean;
  /** Ms since exit began; only meaningful when exitRequested is true. */
  exitElapsedMs: number;
}

export interface LoadingLifecycleResult {
  phase: LoadingPhase;
  /** Visual progress 0–100 (soft-capped while waiting). */
  displayProgress: number;
  /** True when the shell should unmount and reveal the app. */
  shouldUnmount: boolean;
  /** True when readiness + min display are satisfied and exit should begin. */
  shouldStartExit: boolean;
  /** True when maxWait forced completion. */
  timedOut: boolean;
}

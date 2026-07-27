import type { LoadingScreenConfig } from "./types";

/**
 * Jet Stream default boot configuration.
 * Cover art path is the only asset dependency — replace `/brand/loading-cover.svg`
 * or override `coverImageSrc` to swap artwork.
 */
export const DEFAULT_LOADING_SCREEN_CONFIG: LoadingScreenConfig = {
  title: "Jet Stream",
  subtitle: "Clip any length. Frame any ratio. Rank what wins.",
  ariaLabel: "Jet Stream is loading",
  logoSrc: null,
  showBrandMark: true,
  coverImageSrc: "/brand/loading-cover.svg",
  coverFocalPoint: { x: 50, y: 42 },
  fallbackGradient:
    "radial-gradient(ellipse 120% 80% at 50% 20%, hsl(199 60% 18% / 0.55) 0%, transparent 55%), linear-gradient(165deg, hsl(186 42% 7%) 0%, hsl(186 50% 4%) 45%, hsl(200 40% 6%) 100%)",
  overlay: {
    color: "186 50% 3%",
    opacity: 0.55,
    vignetteIntensity: 0.72,
  },
  colors: {
    accent: "199 89% 48%",
    progressTrack: "0 0% 100%",
    progressFill: "199 89% 48%",
    title: "180 12% 96%",
    subtitle: "184 10% 68%",
    status: "184 10% 62%",
  },
  statusMessage: "Loading",
  tips: [
    "Warming the local engine…",
    "Preparing clip studio…",
    "Almost ready…",
  ],
  progressMode: "indeterminate",
  progress: 0,
  timing: {
    minDisplayMs: 1400,
    entranceMs: 800,
    exitMs: 560,
    maxWaitMs: 90_000,
    tipRotateMs: 3200,
  },
  variant: "cinematic",
  reducedMotion: "respect",
  enableGrain: true,
  composition: "lower-left",
};

import type { LoadingScreenConfig, ResolvedLoadingScreenConfig } from "./types";

/** qClip boot defaults — midnight terminal cinematic launcher. */
export const DEFAULT_LOADING_CONFIG: ResolvedLoadingScreenConfig = {
  title: "qClip",
  subtitle: "all-in-one clip studio",
  showLogoMark: true,
  coverSrc: "/loading/cover.svg",
  coverFocalPoint: { x: 50, y: 42 },
  overlayColor: "hsl(186 48% 5%)",
  overlayOpacity: 0.74,
  accentColor: "hsl(199 89% 48%)",
  progressColor: "hsl(199 89% 58%)",
  statusMessage: "Starting studio",
  tips: [
    "Clip any length — warming the engine…",
    "Frame any ratio — preparing reframe…",
    "Rank what wins — almost ready…",
  ],
  tipIntervalMs: 3400,
  progressMode: "indeterminate",
  progress: 0,
  minDisplayMs: 900,
  entranceMs: 680,
  exitMs: 420,
  maxWaitMs: 90_000,
  animationVariant: "cinematic",
  reducedMotion: "respect",
  className: "",
};

export const LOADING_TIPS_DESKTOP: string[] = [
  "Waiting for the local engine…",
  "Preparing clip studio…",
  "Checking encode path…",
];

export function createQClipBootConfig(
  overrides: Partial<LoadingScreenConfig> = {},
): Partial<LoadingScreenConfig> {
  return {
    title: "qClip",
    subtitle: "all-in-one clip studio",
    coverSrc: "/loading/cover.svg",
    statusMessage: "Starting studio",
    tips: LOADING_TIPS_DESKTOP,
    progressMode: "indeterminate",
    animationVariant: "cinematic",
    minDisplayMs: 900,
    entranceMs: 680,
    exitMs: 420,
    maxWaitMs: 90_000,
    reducedMotion: "respect",
    ...overrides,
  };
}

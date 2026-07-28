import { DEFAULT_LOADING_CONFIG } from "./defaults";
import type {
  LoadingAnimationVariant,
  LoadingFocalPoint,
  LoadingProgressMode,
  LoadingScreenConfig,
  ReducedMotionBehavior,
  ResolvedLoadingScreenConfig,
} from "./types";

const ANIMATION_VARIANTS = new Set<LoadingAnimationVariant>([
  "cinematic",
  "minimal",
  "terminal",
]);

const PROGRESS_MODES = new Set<LoadingProgressMode>([
  "determinate",
  "indeterminate",
]);

const REDUCED_MOTION = new Set<ReducedMotionBehavior>([
  "respect",
  "force-full",
  "force-reduced",
]);

function clamp01(n: number): number {
  if (!Number.isFinite(n)) return 0;
  return Math.min(1, Math.max(0, n));
}

function clamp100(n: number): number {
  if (!Number.isFinite(n)) return 0;
  return Math.min(100, Math.max(0, n));
}

function resolveFocal(
  focal: LoadingFocalPoint | undefined,
): LoadingFocalPoint {
  if (!focal) return { ...DEFAULT_LOADING_CONFIG.coverFocalPoint };
  return {
    x: clamp100(focal.x),
    y: clamp100(focal.y),
  };
}

function resolveVariant(
  value: LoadingAnimationVariant | undefined,
): LoadingAnimationVariant {
  if (value && ANIMATION_VARIANTS.has(value)) return value;
  return DEFAULT_LOADING_CONFIG.animationVariant;
}

function resolveProgressMode(
  value: LoadingProgressMode | undefined,
): LoadingProgressMode {
  if (value && PROGRESS_MODES.has(value)) return value;
  return DEFAULT_LOADING_CONFIG.progressMode;
}

function resolveReducedMotion(
  value: ReducedMotionBehavior | undefined,
): ReducedMotionBehavior {
  if (value && REDUCED_MOTION.has(value)) return value;
  return DEFAULT_LOADING_CONFIG.reducedMotion;
}

/**
 * Merge partial config onto qClip defaults.
 * Call sites can pass only title/cover overrides.
 */
export function resolveLoadingConfig(
  partial: Partial<LoadingScreenConfig> = {},
): ResolvedLoadingScreenConfig {
  const tips =
    partial.tips !== undefined
      ? partial.tips.filter((t) => t.trim().length > 0)
      : DEFAULT_LOADING_CONFIG.tips;

  return {
    title: partial.title?.trim() || DEFAULT_LOADING_CONFIG.title,
    subtitle:
      partial.subtitle !== undefined
        ? partial.subtitle
        : DEFAULT_LOADING_CONFIG.subtitle,
    logoSrc: partial.logoSrc?.trim() || undefined,
    showLogoMark:
      partial.showLogoMark ?? DEFAULT_LOADING_CONFIG.showLogoMark,
    coverSrc:
      partial.coverSrc !== undefined
        ? partial.coverSrc?.trim() || undefined
        : DEFAULT_LOADING_CONFIG.coverSrc,
    coverFocalPoint: resolveFocal(partial.coverFocalPoint),
    overlayColor:
      partial.overlayColor?.trim() || DEFAULT_LOADING_CONFIG.overlayColor,
    overlayOpacity: clamp01(
      partial.overlayOpacity ?? DEFAULT_LOADING_CONFIG.overlayOpacity,
    ),
    accentColor:
      partial.accentColor?.trim() || DEFAULT_LOADING_CONFIG.accentColor,
    progressColor:
      partial.progressColor?.trim() || DEFAULT_LOADING_CONFIG.progressColor,
    statusMessage:
      partial.statusMessage?.trim() || DEFAULT_LOADING_CONFIG.statusMessage,
    tips,
    tipIntervalMs: Math.max(
      800,
      partial.tipIntervalMs ?? DEFAULT_LOADING_CONFIG.tipIntervalMs,
    ),
    progressMode: resolveProgressMode(partial.progressMode),
    progress: clamp100(partial.progress ?? DEFAULT_LOADING_CONFIG.progress),
    minDisplayMs: Math.max(
      0,
      partial.minDisplayMs ?? DEFAULT_LOADING_CONFIG.minDisplayMs,
    ),
    entranceMs: Math.max(
      0,
      partial.entranceMs ?? DEFAULT_LOADING_CONFIG.entranceMs,
    ),
    exitMs: Math.max(0, partial.exitMs ?? DEFAULT_LOADING_CONFIG.exitMs),
    maxWaitMs: Math.max(
      1_000,
      partial.maxWaitMs ?? DEFAULT_LOADING_CONFIG.maxWaitMs,
    ),
    animationVariant: resolveVariant(partial.animationVariant),
    reducedMotion: resolveReducedMotion(partial.reducedMotion),
    className: partial.className ?? "",
    onLoadingComplete: partial.onLoadingComplete,
    onTransitionComplete: partial.onTransitionComplete,
  };
}

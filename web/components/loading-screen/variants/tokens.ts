import type { LoadingAnimationVariant } from "../types";

export interface LoadingVariantTokens {
  name: LoadingAnimationVariant;
  coverScaleFrom: number;
  coverScaleTo: number;
  coverDriftPx: number;
  contentTranslateY: number;
  grainOpacity: number;
  accentGlowOpacity: number;
}

export const LOADING_VARIANTS: Record<
  LoadingAnimationVariant,
  LoadingVariantTokens
> = {
  cinematic: {
    name: "cinematic",
    coverScaleFrom: 1.06,
    coverScaleTo: 1.0,
    coverDriftPx: 12,
    contentTranslateY: 14,
    grainOpacity: 0.045,
    accentGlowOpacity: 0.18,
  },
  terminal: {
    name: "terminal",
    coverScaleFrom: 1.02,
    coverScaleTo: 1.0,
    coverDriftPx: 4,
    contentTranslateY: 8,
    grainOpacity: 0.025,
    accentGlowOpacity: 0.08,
  },
  minimal: {
    name: "minimal",
    coverScaleFrom: 1,
    coverScaleTo: 1,
    coverDriftPx: 0,
    contentTranslateY: 0,
    grainOpacity: 0,
    accentGlowOpacity: 0,
  },
};

export function getLoadingVariant(
  name: LoadingAnimationVariant,
): LoadingVariantTokens {
  return LOADING_VARIANTS[name] ?? LOADING_VARIANTS.cinematic;
}

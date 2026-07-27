/**
 * Public API for the Jet Stream cinematic loading-screen system.
 */

export { LoadingScreen } from "./loading-screen";
export type { LoadingScreenProps } from "./loading-screen";

export { DEFAULT_LOADING_SCREEN_CONFIG } from "./defaults";
export {
  resolveLoadingScreenConfig,
  clampProgress,
  softIndeterminateProgress,
} from "./resolve-config";
export { getLoadingVariant, LOADING_VARIANTS } from "./variants/tokens";

export { useLoadingLifecycle } from "./hooks/use-loading-lifecycle";
export { usePrefersReducedMotion } from "./hooks/use-prefers-reduced-motion";
export { useCoverArtPreload } from "./hooks/use-cover-art-preload";
export { useRotatingTips } from "./hooks/use-rotating-tips";

export {
  LoadingScreenProvider,
  useLoadingScreen,
  useLoadingScreenSafe,
} from "./provider/loading-screen-provider";

export type {
  LoadingScreenConfig,
  LoadingScreenConfigInput,
  LoadingScreenPhase,
  LoadingProgressMode,
  LoadingAnimationVariant,
  LoadingLifecycleOptions,
  LoadingLifecycleState,
  ReducedMotionBehavior,
} from "./types";

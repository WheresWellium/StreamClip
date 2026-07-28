export type {
  LoadingAnimationVariant,
  LoadingFocalPoint,
  LoadingLifecycleInput,
  LoadingLifecycleResult,
  LoadingPhase,
  LoadingProgressMode,
  LoadingScreenConfig,
  ReducedMotionBehavior,
  ResolvedLoadingScreenConfig,
} from "./types";

export {
  DEFAULT_LOADING_CONFIG,
  LOADING_TIPS_DESKTOP,
  createQClipBootConfig,
} from "./defaults";

export { resolveLoadingConfig } from "./resolve-config";

export {
  INDETERMINATE_CAP,
  blendDeterminateProgress,
  computeLoadingLifecycle,
  indeterminateProgress,
} from "./lifecycle";

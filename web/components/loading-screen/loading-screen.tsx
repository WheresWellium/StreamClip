"use client";

import type { CSSProperties } from "react";

import { cn } from "@/lib/utils/format";

import { TitleBlock } from "./brand/title-block";
import "./loading-screen.css";
import { useCoverArtPreload } from "./hooks/use-cover-art-preload";
import { usePrefersReducedMotion } from "./hooks/use-prefers-reduced-motion";
import { useRotatingTips } from "./hooks/use-rotating-tips";
import { LoadingProgressBar } from "./indicators/progress-bar";
import { StatusText } from "./indicators/status-text";
import { CoverArtLayer } from "./layers/cover-art";
import { GrainLayer } from "./layers/grain";
import { OverlayVignetteLayer } from "./layers/overlay-vignette";
import { resolveLoadingScreenConfig } from "./resolve-config";
import type {
  LoadingScreenConfigInput,
  LoadingScreenPhase,
  LoadingProgressMode,
} from "./types";
import { getLoadingVariant } from "./variants/tokens";

export interface LoadingScreenProps {
  /** Partial config merged onto Jet Stream defaults. */
  config?: LoadingScreenConfigInput;
  phase?: LoadingScreenPhase;
  /** Override progress display (0–1). */
  progress?: number;
  /** Override progress mode for this render. */
  progressMode?: LoadingProgressMode;
  className?: string;
}

/**
 * Full-viewport cinematic loading shell.
 * Presentational — lifecycle ownership lives in hooks / provider / gate.
 */
export function LoadingScreen({
  config: configInput,
  phase = "loading",
  progress = 0,
  progressMode,
  className,
}: LoadingScreenProps) {
  const config = resolveLoadingScreenConfig(configInput);
  const variant = getLoadingVariant(config.variant);
  const reducedMotion = usePrefersReducedMotion(config.reducedMotion);
  const { loaded, failed } = useCoverArtPreload(config.coverImageSrc);
  const tip = useRotatingTips(
    config.tips,
    config.timing.tipRotateMs,
    phase === "entering" || phase === "loading",
  );

  const mode = progressMode ?? config.progressMode;
  const exiting = phase === "exiting";
  const entering = phase === "entering";

  const compositionClass =
    config.composition === "center"
      ? "items-center justify-center text-center"
      : "items-end justify-start text-left sm:items-end";

  return (
    <div
      className={cn(
        "ls-root fixed inset-0 z-[200] flex min-h-screen w-full overflow-hidden bg-background",
        exiting && "ls-root--exiting",
        entering && "ls-root--entering",
        reducedMotion && "ls-root--reduced",
        `ls-variant-${variant.name}`,
        className,
      )}
      style={
        {
          "--ls-entrance-ms": `${config.timing.entranceMs}ms`,
          "--ls-exit-ms": `${config.timing.exitMs}ms`,
          "--ls-cover-from": String(variant.coverScaleFrom),
          "--ls-cover-to": String(variant.coverScaleTo),
          "--ls-cover-drift": `${variant.coverDriftPx}px`,
          "--ls-content-y": `${variant.contentTranslateY}px`,
        } as CSSProperties
      }
      role="status"
      aria-live="polite"
      aria-busy={phase !== "exiting"}
      aria-label={config.ariaLabel ?? `${config.title} is loading`}
    >
      <CoverArtLayer
        src={config.coverImageSrc}
        focalPoint={config.coverFocalPoint}
        fallbackGradient={config.fallbackGradient}
        imageFailed={failed}
        imageLoaded={loaded}
        reducedMotion={reducedMotion}
      />
      <OverlayVignetteLayer
        overlay={config.overlay}
        accentHsl={config.colors.accent}
        accentGlowOpacity={variant.accentGlowOpacity}
        reducedMotion={reducedMotion}
      />
      <GrainLayer
        opacity={variant.grainOpacity}
        enabled={config.enableGrain}
        reducedMotion={reducedMotion}
      />

      <div
        className={cn(
          "ls-content relative z-10 flex min-h-full w-full p-8 sm:p-12 md:p-16",
          compositionClass,
        )}
      >
        <div className="ls-content__inner w-full max-w-xl">
          <TitleBlock
            title={config.title}
            subtitle={config.subtitle}
            showBrandMark={config.showBrandMark}
            logoSrc={config.logoSrc}
            titleColor={config.colors.title}
            subtitleColor={config.colors.subtitle}
          />
          <div className="mt-10 space-y-4">
            <StatusText
              message={config.statusMessage}
              tip={tip}
              statusColor={config.colors.status}
              reducedMotion={reducedMotion}
            />
            <LoadingProgressBar
              mode={mode}
              progress={progress}
              trackHsl={config.colors.progressTrack}
              fillHsl={config.colors.progressFill}
              reducedMotion={reducedMotion}
            />
          </div>
        </div>
      </div>

      {/* Visually hidden live region keeps SR updates sparse and meaningful */}
      <span className="sr-only">
        {phase === "exiting" ? `${config.title} ready` : config.statusMessage}
      </span>
    </div>
  );
}

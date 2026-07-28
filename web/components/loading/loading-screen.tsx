"use client";

import { useMemo, type CSSProperties } from "react";

import type { LoadingScreenConfig } from "@/lib/loading";
import { BrandBlock } from "./brand-block";
import { CoverArt } from "./cover-art";
import { LoadingOverlay } from "./overlay";
import { LoadingProgressBar } from "./progress-bar";
import { StatusText } from "./status-text";
import { useLoadingLifecycle } from "./use-loading-lifecycle";

export interface LoadingScreenProps {
  /** External readiness (health check, route data, asset bundle, …). */
  isReady: boolean;
  /** Optional real progress 0–100. */
  progress?: number;
  /** Partial config; merges onto qClip defaults. */
  config?: Partial<LoadingScreenConfig>;
  /** Composition: lower-left (default) or center. */
  composition?: "lower-left" | "center";
}

/**
 * Full-viewport cinematic loading shell.
 * Unmounts itself after a clean exit when `isReady` (or maxWait) fires.
 *
 * A11y contract: consumers must not mount interactive app content behind this
 * shell while loading (see SidecarReadyGate — children render only once
 * ready). During the exit crossfade the shell goes `inert` so the now-mounted
 * app receives focus and clicks immediately.
 */
export function LoadingScreen({
  isReady,
  progress,
  config,
  composition = "lower-left",
}: LoadingScreenProps) {
  const {
    phase,
    displayProgress,
    visible,
    exiting,
    timedOut,
    reducedMotion,
    resolved,
    announceText,
  } = useLoadingLifecycle({ isReady, progress, config });

  const rootClass = useMemo(() => {
    const parts = [
      "sc-loading",
      `sc-loading--${resolved.animationVariant}`,
      composition === "center" ? "sc-loading--center" : "",
      exiting ? "sc-loading--exiting" : "",
      timedOut ? "sc-loading--timeout" : "",
      reducedMotion ? "sc-loading--reduced" : "",
      resolved.reducedMotion === "force-full" ? "sc-loading--force-motion" : "",
      resolved.className,
    ];
    return parts.filter(Boolean).join(" ");
  }, [
    composition,
    exiting,
    reducedMotion,
    resolved.animationVariant,
    resolved.className,
    resolved.reducedMotion,
    timedOut,
  ]);

  const style = useMemo(() => {
    return {
      ["--sc-load-accent" as string]: resolved.accentColor,
      ["--sc-load-progress" as string]: resolved.progressColor,
      ["--sc-load-overlay" as string]: resolved.overlayColor,
      ["--sc-load-overlay-opacity" as string]: String(resolved.overlayOpacity),
      ["--sc-load-entrance" as string]: reducedMotion
        ? "0ms"
        : `${resolved.entranceMs}ms`,
      ["--sc-load-exit" as string]: reducedMotion
        ? "140ms"
        : `${resolved.exitMs}ms`,
    } as CSSProperties;
  }, [
    reducedMotion,
    resolved.accentColor,
    resolved.entranceMs,
    resolved.exitMs,
    resolved.overlayColor,
    resolved.overlayOpacity,
    resolved.progressColor,
  ]);

  if (!visible) return null;

  return (
    <div
      className={rootClass}
      style={style}
      role="region"
      aria-busy={!exiting}
      aria-label={`${resolved.title} loading`}
      data-loading-phase={phase}
      data-loading-timeout={timedOut ? "true" : undefined}
      data-testid="app-loading-screen"
      // Decorative chrome must not trap focus; status is announced via live region.
      inert={exiting ? true : undefined}
    >
      <div className="sc-loading__stage" aria-hidden="true">
        <CoverArt
          src={resolved.coverSrc}
          focalX={resolved.coverFocalPoint.x}
          focalY={resolved.coverFocalPoint.y}
        />
        <LoadingOverlay
          color={resolved.overlayColor}
          opacity={resolved.overlayOpacity}
        />
      </div>

      <div className="sc-loading__content">
        <BrandBlock
          title={resolved.title}
          subtitle={resolved.subtitle}
          logoSrc={resolved.logoSrc}
          showLogoMark={resolved.showLogoMark}
          accentColor={resolved.accentColor}
        />
        <StatusText
          message={resolved.statusMessage}
          tips={resolved.tips}
          tipIntervalMs={resolved.tipIntervalMs}
          announceText={announceText}
          reducedMotion={reducedMotion}
        />
        <LoadingProgressBar
          value={displayProgress}
          mode={resolved.progressMode}
          color={resolved.progressColor}
          exiting={exiting}
        />
      </div>
    </div>
  );
}

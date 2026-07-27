"use client";

import { cn } from "@/lib/utils/format";

import type { LoadingScreenOverlayConfig } from "../types";

interface OverlayVignetteLayerProps {
  overlay: LoadingScreenOverlayConfig;
  accentHsl: string;
  accentGlowOpacity: number;
  reducedMotion: boolean;
  className?: string;
}

/**
 * Dark readability overlay + vignette + restrained accent wash.
 */
export function OverlayVignetteLayer({
  overlay,
  accentHsl,
  accentGlowOpacity,
  reducedMotion,
  className,
}: OverlayVignetteLayerProps) {
  const vignette = Math.min(1, Math.max(0, overlay.vignetteIntensity));
  const opacity = Math.min(1, Math.max(0, overlay.opacity));

  return (
    <div
      className={cn("ls-overlay pointer-events-none absolute inset-0", className)}
      aria-hidden="true"
    >
      <div
        className="absolute inset-0"
        style={{
          backgroundColor: `hsl(${overlay.color} / ${opacity})`,
        }}
      />
      <div
        className="absolute inset-0"
        style={{
          background: `radial-gradient(ellipse 75% 65% at 50% 40%, transparent 0%, hsl(186 60% 2% / ${vignette * 0.55}) 70%, hsl(186 70% 1% / ${vignette}) 100%)`,
        }}
      />
      {!reducedMotion && accentGlowOpacity > 0 ? (
        <div
          className="ls-overlay__accent absolute inset-x-0 top-0 h-[42%]"
          style={{
            background: `radial-gradient(ellipse 60% 80% at 50% 0%, hsl(${accentHsl} / ${accentGlowOpacity}) 0%, transparent 70%)`,
          }}
        />
      ) : null}
    </div>
  );
}

"use client";

import { cn } from "@/lib/utils/format";

import type { LoadingScreenFocalPoint } from "../types";

interface CoverArtLayerProps {
  src: string | null;
  focalPoint: LoadingScreenFocalPoint;
  fallbackGradient: string;
  imageFailed: boolean;
  imageLoaded: boolean;
  reducedMotion: boolean;
  className?: string;
}

/**
 * Full-bleed cover / hero background with gradient fallback.
 */
export function CoverArtLayer({
  src,
  focalPoint,
  fallbackGradient,
  imageFailed,
  imageLoaded,
  reducedMotion,
  className,
}: CoverArtLayerProps) {
  const showImage = Boolean(src) && !imageFailed;

  return (
    <div
      className={cn("ls-cover absolute inset-0 overflow-hidden", className)}
      aria-hidden="true"
    >
      <div
        className="absolute inset-0"
        style={{ background: fallbackGradient }}
      />
      {showImage ? (
        // eslint-disable-next-line @next/next/no-img-element -- intentional for /public cover preload path
        <img
          src={src!}
          alt=""
          decoding="async"
          fetchPriority="high"
          draggable={false}
          className={cn(
            "ls-cover__image absolute inset-0 h-full w-full object-cover",
            imageLoaded ? "opacity-100" : "opacity-0",
            !reducedMotion && "ls-cover__image--motion",
          )}
          style={{
            objectPosition: `${focalPoint.x}% ${focalPoint.y}%`,
          }}
        />
      ) : null}
    </div>
  );
}

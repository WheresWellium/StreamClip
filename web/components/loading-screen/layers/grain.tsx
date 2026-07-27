"use client";

import { cn } from "@/lib/utils/format";

interface GrainLayerProps {
  opacity: number;
  enabled: boolean;
  reducedMotion: boolean;
  className?: string;
}

/**
 * Lightweight CSS noise overlay — no canvas loops.
 * Disabled under reduced motion or when opacity is 0.
 */
export function GrainLayer({
  opacity,
  enabled,
  reducedMotion,
  className,
}: GrainLayerProps) {
  if (!enabled || reducedMotion || opacity <= 0) return null;

  return (
    <div
      className={cn("ls-grain pointer-events-none absolute inset-0", className)}
      style={{ opacity }}
      aria-hidden="true"
    />
  );
}

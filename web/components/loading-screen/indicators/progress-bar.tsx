"use client";

import { cn } from "@/lib/utils/format";

import { clampProgress } from "../resolve-config";
import type { LoadingProgressMode } from "../types";

interface LoadingProgressBarProps {
  mode: LoadingProgressMode;
  progress: number;
  trackHsl: string;
  fillHsl: string;
  reducedMotion: boolean;
  className?: string;
}

/**
 * Thin high-end progress track.
 * Determinate uses width; indeterminate uses a sliding shimmer transform.
 */
export function LoadingProgressBar({
  mode,
  progress,
  trackHsl,
  fillHsl,
  reducedMotion,
  className,
}: LoadingProgressBarProps) {
  const value = clampProgress(progress);
  const isDeterminate = mode === "determinate";

  return (
    <div
      className={cn("ls-progress w-full max-w-xs", className)}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={isDeterminate ? Math.round(value * 100) : undefined}
      aria-valuetext={
        isDeterminate ? `${Math.round(value * 100)} percent` : "Loading"
      }
    >
      <div
        className="ls-progress__track relative h-[2px] w-full overflow-hidden"
        style={{ backgroundColor: `hsl(${trackHsl} / 0.18)` }}
      >
        {isDeterminate || value >= 1 ? (
          <div
            className={cn(
              "ls-progress__fill absolute inset-y-0 left-0",
              !reducedMotion && "ls-progress__fill--ease",
            )}
            style={{
              width: `${value * 100}%`,
              backgroundColor: `hsl(${fillHsl})`,
            }}
          />
        ) : reducedMotion ? (
          <div
            className="absolute inset-y-0 left-0 w-1/3"
            style={{ backgroundColor: `hsl(${fillHsl} / 0.7)` }}
          />
        ) : (
          <div
            className="ls-progress__indeterminate absolute inset-y-0 w-1/3"
            style={{ backgroundColor: `hsl(${fillHsl})` }}
          />
        )}
      </div>
    </div>
  );
}

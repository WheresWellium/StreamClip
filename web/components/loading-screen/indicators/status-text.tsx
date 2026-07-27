"use client";

import { cn } from "@/lib/utils/format";

interface StatusTextProps {
  message: string;
  tip?: string | null;
  statusColor: string;
  reducedMotion: boolean;
  className?: string;
}

/**
 * Refined loading label with CSS ellipsis animation.
 * Tip is visual-only to avoid repetitive SR announcements.
 */
export function StatusText({
  message,
  tip,
  statusColor,
  reducedMotion,
  className,
}: StatusTextProps) {
  return (
    <div className={cn("ls-status", className)}>
      <p
        className="font-mono text-[11px] uppercase tracking-[0.16em]"
        style={{ color: `hsl(${statusColor})` }}
      >
        <span>{message}</span>
        {!reducedMotion ? (
          <span className="ls-ellipsis" aria-hidden="true">
            <span>.</span>
            <span>.</span>
            <span>.</span>
          </span>
        ) : (
          <span aria-hidden="true">…</span>
        )}
      </p>
      {tip ? (
        <p
          className="mt-2 text-xs text-muted-foreground/80"
          aria-hidden="true"
        >
          {tip}
        </p>
      ) : null}
    </div>
  );
}

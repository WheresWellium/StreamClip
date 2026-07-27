"use client";

import { cn } from "@/lib/utils/format";

interface BrandMarkProps {
  logoSrc?: string | null;
  className?: string;
}

/**
 * Default Jet Stream mark (inline SVG) or optional image logo.
 */
export function BrandMark({ logoSrc, className }: BrandMarkProps) {
  if (logoSrc) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={logoSrc}
        alt=""
        width={28}
        height={28}
        className={cn("h-7 w-7 object-contain", className)}
        aria-hidden="true"
        draggable={false}
      />
    );
  }

  return (
    <span
      className={cn(
        "flex h-7 w-7 items-center justify-center border border-sky-400 text-sky-400",
        className,
      )}
      aria-hidden="true"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <path d="M2 21l21-9L2 3v7l15 2-15 2z" />
      </svg>
    </span>
  );
}

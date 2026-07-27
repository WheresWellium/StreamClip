"use client";

import { cn } from "@/lib/utils/format";

import { BrandMark } from "./brand-mark";

interface TitleBlockProps {
  title: string;
  subtitle?: string;
  showBrandMark: boolean;
  logoSrc?: string | null;
  titleColor: string;
  subtitleColor: string;
  className?: string;
}

/**
 * Large title + optional subtitle / brand mark.
 */
export function TitleBlock({
  title,
  subtitle,
  showBrandMark,
  logoSrc,
  titleColor,
  subtitleColor,
  className,
}: TitleBlockProps) {
  return (
    <div className={cn("ls-title-block", className)}>
      {showBrandMark ? (
        <div className="mb-5">
          <BrandMark logoSrc={logoSrc} />
        </div>
      ) : null}
      <p className="term-label mb-3 text-sky-400/90">Studio boot</p>
      <h1
        className="font-sans text-4xl font-medium tracking-tight sm:text-5xl md:text-6xl"
        style={{ color: `hsl(${titleColor})` }}
      >
        {title}
      </h1>
      {subtitle ? (
        <p
          className="mt-3 max-w-md text-sm leading-relaxed sm:text-base"
          style={{ color: `hsl(${subtitleColor})` }}
        >
          {subtitle}
        </p>
      ) : null}
    </div>
  );
}

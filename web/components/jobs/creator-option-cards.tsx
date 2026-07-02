"use client";

import * as React from "react";

import { HelpTip } from "@/components/ui/help-tip";
import type { CreatorMetaOption } from "@/lib/creator-option-ids";
import { cn } from "@/lib/utils/format";

type Props = {
  title: string;
  tip?: string;
  options: CreatorMetaOption[];
  value: string;
  onChange: (id: string) => void;
  columns?: 1 | 2 | 3;
  showAspectBadge?: boolean;
  showPlatformChips?: boolean;
};

export function CreatorOptionCards({
  title,
  tip,
  options,
  value,
  onChange,
  columns = 2,
  showAspectBadge = false,
  showPlatformChips = false,
}: Props) {
  const gridClass =
    columns === 3
      ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
      : columns === 1
        ? "grid-cols-1"
        : "grid-cols-1 sm:grid-cols-2";

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1.5">
        <span className="text-sm font-medium">{title}</span>
        {tip ? <HelpTip content={tip} label={`${title} help`} /> : null}
      </div>
      <div className={cn("grid gap-2", gridClass)}>
        {options.map((option) => {
          const selected = value === option.id;
          return (
            <button
              key={option.id}
              type="button"
              onClick={() => onChange(option.id)}
              className={cn(
                "flex flex-col items-start gap-2 p-3 rounded-lg text-left transition-all border min-h-[44px]",
                selected
                  ? "border-sky-400/50 bg-sky-400/10 text-foreground sky-glow"
                  : "border-white/10 bg-black/20 hover:border-white/20 hover:bg-white/5",
              )}
            >
              <div className="flex items-start justify-between gap-2 w-full">
                <span className="text-sm font-medium leading-snug">{option.label}</span>
                {showAspectBadge && option.aspect_ratio && (
                  <span className="shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded bg-black/40 text-sky-300 border border-sky-500/30">
                    {option.aspect_ratio}
                  </span>
                )}
              </div>
              {option.description && (
                <span className="text-xs text-muted-foreground line-clamp-2">
                  {option.description}
                </span>
              )}
              {option.best_for && (
                <span className="text-[10px] text-muted-foreground/90">
                  <span className="text-silver uppercase tracking-wide">Best for </span>
                  {option.best_for}
                </span>
              )}
              {option.preview_hint && (
                <span className="text-[10px] font-mono text-sky-400/80">{option.preview_hint}</span>
              )}
              {showAspectBadge && option.output_resolution && (
                <span className="text-[10px] text-muted-foreground">
                  Output {option.output_resolution}
                </span>
              )}
              {showPlatformChips && option.platforms && option.platforms.length > 0 && (
                <div className="flex flex-wrap gap-1 pt-0.5">
                  {option.platforms.slice(0, 4).map((p) => (
                    <span
                      key={p}
                      className="text-[9px] px-1.5 py-0.5 rounded-full bg-white/5 text-muted-foreground border border-white/10"
                    >
                      {p}
                    </span>
                  ))}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

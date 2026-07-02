"use client";

import * as React from "react";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils/format";

interface SectionLegendProps {
  title: string;
  tip: React.ReactNode;
  className?: string;
}

/** Section header — hover the label itself for the legend (no icon). */
export function SectionLegend({ title, tip, className }: SectionLegendProps) {
  return (
    <div className={cn("flex items-center", className)}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className="term-label cursor-help underline decoration-dotted decoration-frame/30 underline-offset-4"
            aria-label={`${title} section help`}
          >
            {title}
          </span>
        </TooltipTrigger>
        <TooltipContent side="top">{tip}</TooltipContent>
      </Tooltip>
    </div>
  );
}

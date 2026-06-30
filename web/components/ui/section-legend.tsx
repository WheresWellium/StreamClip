"use client";

import * as React from "react";

import { HelpTip } from "@/components/ui/help-tip";
import { cn } from "@/lib/utils/format";

interface SectionLegendProps {
  title: string;
  tip: React.ReactNode;
  className?: string;
}

/** Section header with an info icon legend. */
export function SectionLegend({ title, tip, className }: SectionLegendProps) {
  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {title}
      </span>
      <HelpTip content={tip} label={`${title} section help`} />
    </div>
  );
}

"use client";

import * as React from "react";

import { Badge } from "@/components/ui/form";
import { HelpTip } from "@/components/ui/help-tip";
import { cn } from "@/lib/utils/format";

interface LegendBadgeProps {
  children: React.ReactNode;
  className?: string;
  tip: React.ReactNode;
  tipLabel?: string;
}

/** Badge with an adjacent info icon explaining the label. */
export function LegendBadge({
  children,
  className,
  tip,
  tipLabel = "Badge help",
}: LegendBadgeProps) {
  return (
    <span className="inline-flex items-center gap-1">
      <Badge className={className}>{children}</Badge>
      <HelpTip
        content={tip}
        label={tipLabel}
        className="h-3 w-3 [&_svg]:h-2.5 [&_svg]:w-2.5"
      />
    </span>
  );
}

interface LegendLabelProps {
  children: React.ReactNode;
  tip: React.ReactNode;
  tipLabel?: string;
  className?: string;
}

/** Small label (mono corner tags) with info icon. */
export function LegendLabel({
  children,
  tip,
  tipLabel = "Label help",
  className,
}: LegendLabelProps) {
  return (
    <span className={cn("inline-flex items-center gap-0.5", className)}>
      <span>{children}</span>
      <HelpTip
        content={tip}
        label={tipLabel}
        className="h-3 w-3 [&_svg]:h-2.5 [&_svg]:w-2.5 text-white/80 hover:text-white"
      />
    </span>
  );
}

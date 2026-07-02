"use client";

import * as React from "react";

import { Badge } from "@/components/ui/form";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils/format";

interface LegendBadgeProps {
  children: React.ReactNode;
  className?: string;
  tip: React.ReactNode;
  tipLabel?: string;
}

/** Badge that explains itself on hover — no extra icon. */
export function LegendBadge({
  children,
  className,
  tip,
  tipLabel = "Badge help",
}: LegendBadgeProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          className={cn("cursor-default", className)}
          aria-label={tipLabel}
          tabIndex={0}
        >
          {children}
        </Badge>
      </TooltipTrigger>
      <TooltipContent side="top">{tip}</TooltipContent>
    </Tooltip>
  );
}

interface LegendLabelProps {
  children: React.ReactNode;
  tip: React.ReactNode;
  tipLabel?: string;
  className?: string;
}

/** Small label (mono corner tags) that explains itself on hover. */
export function LegendLabel({
  children,
  tip,
  tipLabel = "Label help",
  className,
}: LegendLabelProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn("cursor-default", className)}
          aria-label={tipLabel}
          tabIndex={0}
        >
          {children}
        </span>
      </TooltipTrigger>
      <TooltipContent side="top">{tip}</TooltipContent>
    </Tooltip>
  );
}

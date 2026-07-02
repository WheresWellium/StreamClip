"use client";

import { CircleHelp } from "lucide-react";
import * as React from "react";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils/format";

interface HelpTipProps {
  /** Plain-language definition shown on hover/focus. */
  content: React.ReactNode;
  className?: string;
  /** Visually hidden label for screen readers. */
  label?: string;
}

/**
 * Small (?) icon — reserve for controls whose purpose genuinely needs
 * explanation. Prefer LegendLabel / SectionLegend (hover-on-text) elsewhere.
 */
export function HelpTip({ content, className, label = "More info" }: HelpTipProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex shrink-0 items-center justify-center text-muted-foreground/60 hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring transition-colors",
            className,
          )}
          aria-label={label}
        >
          <CircleHelp className="h-3 w-3" aria-hidden />
        </button>
      </TooltipTrigger>
      <TooltipContent side="top">{content}</TooltipContent>
    </Tooltip>
  );
}

interface LabelWithTipProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  tip: React.ReactNode;
  tipLabel?: string;
}

/** Form label — hover the text itself for help (no icon). */
export function LabelWithTip({
  tip,
  tipLabel,
  children,
  className,
  ...props
}: LabelWithTipProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <label
          className={cn(
            "inline-block w-fit cursor-help text-sm font-medium leading-none underline decoration-dotted decoration-frame/25 underline-offset-4 peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
            className,
          )}
          aria-label={tipLabel}
          {...props}
        >
          {children}
        </label>
      </TooltipTrigger>
      <TooltipContent side="top">{tip}</TooltipContent>
    </Tooltip>
  );
}

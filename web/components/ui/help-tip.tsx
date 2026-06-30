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
 * Small (?) icon — hover or focus to read what a control does.
 */
export function HelpTip({ content, className, label = "More info" }: HelpTipProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex shrink-0 items-center justify-center rounded-full text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background transition-colors",
            className,
          )}
          aria-label={label}
        >
          <CircleHelp className="h-3.5 w-3.5" aria-hidden />
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" className="leading-relaxed">
        {content}
      </TooltipContent>
    </Tooltip>
  );
}

interface LabelWithTipProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  tip: React.ReactNode;
  tipLabel?: string;
}

/** Form label with an inline help icon. */
export function LabelWithTip({
  tip,
  tipLabel,
  children,
  className,
  ...props
}: LabelWithTipProps) {
  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <label
        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
        {...props}
      >
        {children}
      </label>
      <HelpTip content={tip} label={tipLabel} />
    </div>
  );
}

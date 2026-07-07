"use client";

import { ChevronDown } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils/format";

type Props = {
  title: React.ReactNode;
  summary?: React.ReactNode;
  defaultOpen?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: React.ReactNode;
  className?: string;
  contentClassName?: string;
};

export function CollapsibleSection({
  title,
  summary,
  defaultOpen = false,
  open: controlledOpen,
  onOpenChange,
  children,
  className,
  contentClassName,
}: Props) {
  const [internalOpen, setInternalOpen] = React.useState(defaultOpen);
  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : internalOpen;

  function toggle() {
    const next = !open;
    if (!isControlled) setInternalOpen(next);
    onOpenChange?.(next);
  }

  return (
    <div className={cn("rounded-lg border border-border/50 bg-card/40", className)}>
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-frame/5 transition-colors"
      >
        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 text-muted-foreground transition-transform",
            open && "rotate-180",
          )}
        />
        <span className="flex-1 min-w-0">
          <span className="block text-sm font-medium text-foreground">{title}</span>
          {summary && !open && (
            <span className="block text-xs text-muted-foreground truncate mt-0.5">
              {summary}
            </span>
          )}
        </span>
      </button>
      {open && (
        <div className={cn("border-t border-border/40 px-3 py-3", contentClassName)}>
          {children}
        </div>
      )}
    </div>
  );
}

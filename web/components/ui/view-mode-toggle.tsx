"use client";

import { LayoutGrid, List } from "lucide-react";

import type { ViewMode } from "@/lib/view-mode";
import { cn } from "@/lib/utils/format";

type Props = {
  mode: ViewMode;
  onChange: (mode: ViewMode) => void;
  listLabel?: string;
  cardLabel?: string;
};

export function ViewModeToggle({
  mode,
  onChange,
  listLabel = "List",
  cardLabel = "Cards",
}: Props) {
  return (
    <div
      className="inline-flex rounded-sm border border-frame/25 overflow-hidden text-xs"
      role="group"
      aria-label="View mode"
    >
      <button
        type="button"
        aria-pressed={mode === "list"}
        className={cn(
          "inline-flex items-center gap-1 px-2.5 py-1.5 transition-colors",
          mode === "list"
            ? "bg-sky-400/15 text-sky-400"
            : "text-muted-foreground hover:text-foreground hover:bg-frame/5",
        )}
        onClick={() => onChange("list")}
      >
        <List className="h-3.5 w-3.5" />
        {listLabel}
      </button>
      <button
        type="button"
        aria-pressed={mode === "card"}
        className={cn(
          "inline-flex items-center gap-1 px-2.5 py-1.5 border-l border-frame/25 transition-colors",
          mode === "card"
            ? "bg-sky-400/15 text-sky-400"
            : "text-muted-foreground hover:text-foreground hover:bg-frame/5",
        )}
        onClick={() => onChange("card")}
      >
        <LayoutGrid className="h-3.5 w-3.5" />
        {cardLabel}
      </button>
    </div>
  );
}

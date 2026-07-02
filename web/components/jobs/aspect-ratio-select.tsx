"use client";

import { Check, ChevronDown, Proportions } from "lucide-react";
import * as React from "react";

import { Label } from "@/components/ui/form";
import type { AspectRatioOption } from "@/lib/api/meta-types";
import { cn } from "@/lib/utils/format";

// Fallback catalog when /api/meta hasn't been refreshed yet.
const DEFAULT_OPTIONS: AspectRatioOption[] = [
  {
    id: "9:16",
    label: "Vertical 9:16",
    width: 1080,
    height: 1920,
    output_resolution: "1080×1920",
    aspect_ratio: "9:16",
    description: "Full-screen vertical — the short-form default.",
    platforms: ["TikTok", "YouTube Shorts", "Instagram Reels", "Snap Spotlight"],
  },
  {
    id: "1:1",
    label: "Square 1:1",
    width: 1080,
    height: 1080,
    output_resolution: "1080×1080",
    aspect_ratio: "1:1",
    description: "Square feed post — maximum feed real estate on X and LinkedIn.",
    platforms: ["Instagram Feed", "X / Twitter", "LinkedIn", "Facebook"],
  },
  {
    id: "4:5",
    label: "Portrait 4:5",
    width: 1080,
    height: 1350,
    output_resolution: "1080×1350",
    aspect_ratio: "4:5",
    description: "Tall feed post — the largest format Instagram allows in-feed.",
    platforms: ["Instagram Feed", "Facebook Feed"],
  },
  {
    id: "16:9",
    label: "Landscape 16:9",
    width: 1920,
    height: 1080,
    output_resolution: "1920×1080",
    aspect_ratio: "16:9",
    description: "Widescreen — standard for YouTube and landscape embeds.",
    platforms: ["YouTube", "X / Twitter", "LinkedIn", "Facebook"],
  },
  {
    id: "2:3",
    label: "Portrait 2:3",
    width: 1080,
    height: 1620,
    output_resolution: "1080×1620",
    aspect_ratio: "2:3",
    description: "Tall pin format — Pinterest's recommended video ratio.",
    platforms: ["Pinterest"],
  },
];

function RatioThumb({ width, height }: { width: number; height: number }) {
  // Draw a miniature frame proportional to the export dimensions.
  const maxSide = 22;
  const scale = maxSide / Math.max(width, height);
  return (
    <span
      className="inline-flex items-center justify-center shrink-0"
      style={{ width: maxSide, height: maxSide }}
      aria-hidden
    >
      <span
        className="rounded-[2px] border border-sky-400/70 bg-sky-400/10"
        style={{ width: Math.round(width * scale), height: Math.round(height * scale) }}
      />
    </span>
  );
}

type Props = {
  value: string;
  onChange: (id: string) => void;
  options?: AspectRatioOption[];
  label?: string;
  compact?: boolean;
  disabled?: boolean;
};

export function AspectRatioSelect({
  value,
  onChange,
  options,
  label = "Export aspect ratio",
  compact = false,
  disabled = false,
}: Props) {
  const catalog = options && options.length > 0 ? options : DEFAULT_OPTIONS;
  const [open, setOpen] = React.useState(false);
  const rootRef = React.useRef<HTMLDivElement | null>(null);

  const selected = catalog.find((o) => o.id === value) ?? catalog[0];

  React.useEffect(() => {
    if (!open) return;
    function onPointerDown(e: PointerEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative space-y-1.5">
      <Label className={cn(compact && "text-xs")}>{label}</Label>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={cn(
          "flex w-full items-center gap-2.5 rounded-md border border-input bg-background px-3 text-left text-sm",
          "shadow-sm transition-colors hover:border-sky-400/40 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
          "disabled:cursor-not-allowed disabled:opacity-50",
          compact ? "py-1.5" : "py-2",
        )}
      >
        <Proportions className="h-4 w-4 shrink-0 text-sky-400" />
        <RatioThumb width={selected.width} height={selected.height} />
        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium">{selected.label}</span>
          <span className="block truncate text-xs text-muted-foreground">
            {selected.output_resolution}
            {selected.platforms?.length ? ` · ${selected.platforms.join(", ")}` : ""}
          </span>
        </span>
        <ChevronDown
          className={cn("h-4 w-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")}
        />
      </button>

      {open && (
        <ul
          role="listbox"
          aria-label={label}
          className="absolute z-30 mt-1 w-full overflow-hidden rounded-md border border-border bg-popover shadow-xl"
        >
          {catalog.map((option) => {
            const active = option.id === selected.id;
            return (
              <li key={option.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={active}
                  onClick={() => {
                    onChange(option.id);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex w-full items-start gap-2.5 px-3 py-2.5 text-left text-sm transition-colors",
                    active ? "bg-sky-400/10" : "hover:bg-white/5",
                  )}
                >
                  <RatioThumb width={option.width} height={option.height} />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2">
                      <span className="font-medium">{option.label}</span>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {option.output_resolution}
                      </span>
                    </span>
                    {option.description && (
                      <span className="mt-0.5 block text-xs text-muted-foreground line-clamp-1">
                        {option.description}
                      </span>
                    )}
                    {option.platforms && option.platforms.length > 0 && (
                      <span className="mt-1 flex flex-wrap gap-1">
                        {option.platforms.map((p) => (
                          <span
                            key={p}
                            className="rounded-full border border-white/10 bg-black/20 px-1.5 py-0.5 text-[9px] text-muted-foreground"
                          >
                            {p}
                          </span>
                        ))}
                      </span>
                    )}
                  </span>
                  {active && <Check className="mt-0.5 h-4 w-4 shrink-0 text-sky-400" />}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function aspectRatioCss(id: string): string {
  const option = DEFAULT_OPTIONS.find((o) => o.id === id);
  if (!option) return "9/16";
  return `${option.width}/${option.height}`;
}

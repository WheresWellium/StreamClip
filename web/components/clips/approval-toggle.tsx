"use client";

import { cn } from "@/lib/utils/format";

export type ApprovalValue = "draft" | "approved" | "rejected";

const OPTIONS: { value: ApprovalValue; label: string }[] = [
  { value: "draft", label: "Draft" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

type Props = {
  value: ApprovalValue;
  onChange: (value: ApprovalValue) => void;
  disabled?: boolean;
};

export function ApprovalToggle({ value, onChange, disabled }: Props) {
  return (
    <div
      role="radiogroup"
      aria-label="Approval status"
      className="flex rounded-md border border-border/60 overflow-hidden text-[10px]"
    >
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          role="radio"
          aria-checked={value === opt.value}
          disabled={disabled}
          onClick={() => onChange(opt.value)}
          className={cn(
            "flex-1 px-2 py-1.5 min-h-[44px] sm:min-h-0 transition-colors",
            value === opt.value
              ? opt.value === "approved"
                ? "bg-emerald-600/30 text-emerald-100"
                : opt.value === "rejected"
                  ? "bg-destructive/20 text-destructive"
                  : "bg-sky-600/25 text-sky-100"
              : "text-muted-foreground hover:bg-secondary/50",
            disabled && "opacity-50 cursor-not-allowed",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

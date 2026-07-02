import * as React from "react";
import { cn } from "@/lib/utils/format";

// ─── Input ────────────────────────────────────────────────────────────────────

const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, type, ...props }, ref) => (
  <input
    type={type}
      className={cn(
        "flex h-9 w-full rounded-md border border-white/10 bg-black/20 px-3 py-1 text-sm shadow-inner transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-sky-400/60 disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
    ref={ref}
    {...props}
  />
));
Input.displayName = "Input";

// ─── Label ────────────────────────────────────────────────────────────────────

const Label = React.forwardRef<
  HTMLLabelElement,
  React.LabelHTMLAttributes<HTMLLabelElement>
>(({ className, ...props }, ref) => (
  <label
    ref={ref}
    className={cn(
      "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
      className,
    )}
    {...props}
  />
));
Label.displayName = "Label";

// ─── Select (native) ──────────────────────────────────────────────────────────

const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <select
    ref={ref}
      className={cn(
      "flex h-9 w-full items-center rounded-md border border-white/10 bg-black/20 px-3 py-1 text-sm shadow-inner focus:outline-none focus:ring-1 focus:ring-sky-400/60 disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
    {...props}
  >
    {children}
  </select>
));
Select.displayName = "Select";

// ─── Badge ────────────────────────────────────────────────────────────────────

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium",
        className,
      )}
      {...props}
    />
  ),
);
Badge.displayName = "Badge";

// ─── Progress (inline, no radix needed) ──────────────────────────────────────

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number; // 0..1
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ value, className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "relative h-2 w-full overflow-hidden rounded-full bg-white/5 border border-white/5",
        className,
      )}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={1}
      aria-valuenow={Math.max(0, Math.min(1, value))}
      {...props}
    >
      <div
        className="h-full rounded-full bg-gradient-to-r from-sky-500 to-sky-400 transition-all duration-500 ease-out progress-bar shadow-[0_0_8px_rgba(56,189,248,0.4)]"
        style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }}
      />
    </div>
  ),
);
Progress.displayName = "Progress";

export { Input, Label, Select, Badge, Progress };

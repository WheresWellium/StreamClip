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
        "flex h-8 w-full rounded-sm border border-frame/20 bg-input px-2.5 py-1 text-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:border-sky-400 focus-visible:ring-0 disabled:cursor-not-allowed disabled:opacity-50",
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
      "flex h-8 w-full items-center rounded-sm border border-frame/20 bg-input px-2.5 py-1 text-sm focus:outline-none focus:border-sky-400 disabled:cursor-not-allowed disabled:opacity-50",
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
        "inline-flex items-center rounded-sm border px-1.5 py-px font-mono text-[10px] font-medium uppercase tracking-wide",
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
        "relative h-1.5 w-full overflow-hidden rounded-none bg-frame/10 border border-frame/15",
        className,
      )}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={1}
      aria-valuenow={Math.max(0, Math.min(1, value))}
      {...props}
    >
      <div
        className="h-full bg-sky-400 transition-all duration-500 ease-out progress-bar"
        style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }}
      />
    </div>
  ),
);
Progress.displayName = "Progress";

export { Input, Label, Select, Badge, Progress };

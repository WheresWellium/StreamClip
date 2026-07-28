import type { CSSProperties } from "react";

interface LoadingProgressBarProps {
  value: number;
  mode: "determinate" | "indeterminate";
  color: string;
  exiting: boolean;
}

export function LoadingProgressBar({
  value,
  mode,
  color,
  exiting,
}: LoadingProgressBarProps) {
  const determinate = mode === "determinate" || exiting;
  const width = Math.min(100, Math.max(0, value));
  const rounded = Math.round(width);

  return (
    <div
      className={
        determinate
          ? "sc-loading__progress"
          : "sc-loading__progress sc-loading__progress--indeterminate"
      }
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={determinate ? rounded : undefined}
      aria-valuetext={
        determinate ? `${rounded} percent` : "Loading in progress"
      }
      aria-label="Loading progress"
    >
      <div className="sc-loading__progress-track">
        <div
          className="sc-loading__progress-fill"
          style={
            {
              ["--sc-load-progress" as string]: color,
              ...(determinate
                ? { ["--sc-load-progress-width" as string]: `${width}%` }
                : null),
            } as CSSProperties
          }
        />
      </div>
    </div>
  );
}

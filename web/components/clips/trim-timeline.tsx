"use client";

import * as React from "react";

import { getJobWaveformAction } from "@/lib/api/actions/jobs";
import { cn, formatDuration } from "@/lib/utils/format";

type DragTarget = "start" | "end" | null;

type Props = {
  jobId: string;
  /** Full source duration (timeline domain). */
  maxSecs: number;
  start: number;
  end: number;
  minClipSecs: number;
  onChange: (start: number, end: number) => void;
  disabled?: boolean;
};

/**
 * Phase 2b-ii — waveform trim timeline. The source waveform (rendered once
 * per job during ingest) is the track background; the clip window is
 * adjusted by dragging the edge handles or the window body.
 */
export function TrimTimeline({
  jobId,
  maxSecs,
  start,
  end,
  minClipSecs,
  onChange,
  disabled = false,
}: Props) {
  const trackRef = React.useRef<HTMLDivElement>(null);
  const [waveformUrl, setWaveformUrl] = React.useState<string | null>(null);
  const [drag, setDrag] = React.useState<DragTarget>(null);

  React.useEffect(() => {
    let cancelled = false;
    getJobWaveformAction(jobId).then((result) => {
      if (!cancelled && result.ok) setWaveformUrl(result.url);
    });
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  const domain = Math.max(maxSecs, end, 1);
  const startFrac = Math.min(start / domain, 1);
  const endFrac = Math.min(end / domain, 1);

  const secsAtPointer = React.useCallback(
    (clientX: number): number => {
      const track = trackRef.current;
      if (!track) return 0;
      const rect = track.getBoundingClientRect();
      const frac = Math.min(Math.max((clientX - rect.left) / rect.width, 0), 1);
      return frac * domain;
    },
    [domain],
  );

  React.useEffect(() => {
    if (!drag) return;

    function onMove(e: PointerEvent) {
      const secs = secsAtPointer(e.clientX);
      if (drag === "start") {
        onChange(Math.min(secs, end - minClipSecs), end);
      } else if (drag === "end") {
        onChange(start, Math.max(secs, start + minClipSecs));
      }
    }
    function onUp() {
      setDrag(null);
    }

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp, { once: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, [drag, start, end, minClipSecs, onChange, secsAtPointer]);

  function beginDrag(target: Exclude<DragTarget, null>) {
    return (e: React.PointerEvent) => {
      if (disabled) return;
      e.preventDefault();
      setDrag(target);
    };
  }

  return (
    <div className="space-y-1">
      <div
        ref={trackRef}
        className={cn(
          "relative h-16 rounded-md border border-border/60 bg-black/60 overflow-hidden select-none",
          drag && "cursor-ew-resize",
        )}
      >
        {waveformUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={waveformUrl}
            alt="Source audio waveform"
            className="absolute inset-0 h-full w-full object-fill opacity-60 pointer-events-none"
            draggable={false}
          />
        ) : (
          <div className="absolute inset-0 grid place-items-center text-[10px] text-muted-foreground pointer-events-none">
            Waveform unavailable
          </div>
        )}

        {/* Dimmed out-of-window regions */}
        <div
          className="absolute inset-y-0 left-0 bg-black/60 pointer-events-none"
          style={{ width: `${startFrac * 100}%` }}
        />
        <div
          className="absolute inset-y-0 right-0 bg-black/60 pointer-events-none"
          style={{ width: `${(1 - endFrac) * 100}%` }}
        />

        {/* Clip window */}
        <div
          className="absolute inset-y-0 border-x-2 border-sky-400 bg-sky-400/10"
          style={{
            left: `${startFrac * 100}%`,
            width: `${Math.max(0, (endFrac - startFrac) * 100)}%`,
          }}
        >
          <span className="absolute left-1/2 top-1 -translate-x-1/2 rounded bg-black/70 px-1.5 py-0.5 text-[10px] font-mono text-sky-300 pointer-events-none">
            {formatDuration(end - start)}
          </span>
        </div>

        {/* Drag handles */}
        <button
          type="button"
          aria-label={`Clip start: ${start.toFixed(1)} seconds`}
          onPointerDown={beginDrag("start")}
          disabled={disabled}
          className="absolute inset-y-0 w-4 -ml-2 cursor-ew-resize touch-none group"
          style={{ left: `${startFrac * 100}%` }}
        >
          <span className="absolute inset-y-2 left-1/2 w-1.5 -translate-x-1/2 rounded-full bg-sky-400 group-hover:bg-sky-300 group-active:bg-sky-200" />
        </button>
        <button
          type="button"
          aria-label={`Clip end: ${end.toFixed(1)} seconds`}
          onPointerDown={beginDrag("end")}
          disabled={disabled}
          className="absolute inset-y-0 w-4 -ml-2 cursor-ew-resize touch-none group"
          style={{ left: `${endFrac * 100}%` }}
        >
          <span className="absolute inset-y-2 left-1/2 w-1.5 -translate-x-1/2 rounded-full bg-sky-400 group-hover:bg-sky-300 group-active:bg-sky-200" />
        </button>
      </div>

      <div className="flex justify-between text-[10px] font-mono text-muted-foreground">
        <span>0:00</span>
        <span>{formatDuration(domain)}</span>
      </div>
    </div>
  );
}

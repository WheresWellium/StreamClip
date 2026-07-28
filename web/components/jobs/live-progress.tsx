"use client";

import { Check, CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { Progress } from "@/components/ui/form";
import { LegendBadge, LegendLabel } from "@/components/ui/legend-badge";
import { useToastSafe } from "@/components/providers/toast-provider";
import { useJobProgress } from "@/lib/api/use-job-progress";
import type { ProgressEvent, StageDurations } from "@/lib/api/types";
import {
  PROGRESS_LEGEND,
  legendForPipelineStep,
  legendForStage,
  legendForStatus,
} from "@/lib/help/legends";
import { userFacingErrorMessage } from "@/lib/help/user-errors";
import {
  formatDurationSeconds,
  formatEtaRemaining,
  parseIngestSubProgress,
} from "@/lib/utils/duration";
import { cn, statusColors } from "@/lib/utils/format";

interface LiveProgressProps {
  jobId: string;
  initialStatus: string;
  initialProgress: number;
  initialStage: string;
  initialStageDurations?: StageDurations | null;
  initialTotalElapsedSecs?: number | null;
}

const TERMINAL = new Set(["done", "error", "cancelled"]);

/** Matches backend `core.eta.STAGE_ALIASES`. */
const STAGE_ALIASES: Record<string, string> = {
  queued: "ingest",
  ingesting: "ingest",
  ingested: "ingest",
  transcribing: "transcribe",
  transcribed: "transcribe",
  detecting: "highlights",
  detected: "highlights",
  scoring_virality: "virality",
  virality_scored: "virality",
  processing: "process_clip",
  rendering: "process_clip",
  reframe: "process_clip",
  caption: "process_clip",
  overlay: "process_clip",
  completed: "process_clip",
  done: "process_clip",
};

const PIPELINE_STEPS = [
  { key: "ingest", label: "Ingest" },
  { key: "transcribe", label: "Transcribe" },
  { key: "highlights", label: "Detect" },
  { key: "virality", label: "Score" },
  { key: "process_clip", label: "Render" },
] as const;

function canonicalStage(stage: string): string {
  const base = stage.split("/")[0];
  return STAGE_ALIASES[stage] ?? STAGE_ALIASES[base] ?? base;
}

function stepIndex(key: string): number {
  return PIPELINE_STEPS.findIndex((s) => s.key === key);
}

function useLiveSeconds(
  baseSecs: number | null | undefined,
  enabled: boolean,
  direction: "up" | "down" = "up",
): number | null {
  const anchorRef = React.useRef<{ base: number; at: number } | null>(null);
  const [, tick] = React.useReducer((n: number) => n + 1, 0);

  React.useEffect(() => {
    if (baseSecs == null || !Number.isFinite(baseSecs)) {
      anchorRef.current = null;
      return;
    }
    anchorRef.current = { base: baseSecs, at: Date.now() };
  }, [baseSecs]);

  React.useEffect(() => {
    if (!enabled || anchorRef.current == null) return;
    const id = window.setInterval(() => tick(), 1000);
    return () => window.clearInterval(id);
  }, [enabled, baseSecs]);

  if (baseSecs == null || !Number.isFinite(baseSecs)) return null;
  const anchor = anchorRef.current;
  if (!anchor) return baseSecs;
  const delta = (Date.now() - anchor.at) / 1000;
  if (direction === "down") {
    return Math.max(0, anchor.base - delta);
  }
  return anchor.base + delta;
}

function PipelineStepper({
  currentStage,
  stageDurations,
  finished,
}: {
  currentStage: string;
  stageDurations: StageDurations;
  finished: boolean;
}) {
  const currentKey = canonicalStage(currentStage);
  const currentIdx = stepIndex(currentKey);

  return (
    <div className="space-y-2">
      <LegendLabel
        tip={PROGRESS_LEGEND.stepper}
        tipLabel="Pipeline stepper help"
        className="term-label"
      >
        Pipeline
      </LegendLabel>
      <ol className="flex items-center gap-1 sm:gap-2">
        {PIPELINE_STEPS.map((step, idx) => {
          const isComplete =
            finished || (currentIdx >= 0 && idx < currentIdx);
          const isCurrent = !finished && currentIdx === idx;
          const isPending = !finished && currentIdx >= 0 && idx > currentIdx;
          const duration = stageDurations[step.key];

          return (
            <li
              key={step.key}
              className="flex flex-1 flex-col items-center gap-1 min-w-0"
            >
              <div className="flex items-center w-full">
                {idx > 0 && (
                  <div
                    className={cn(
                      "h-px flex-1",
                      isComplete ? "bg-sky-400/60" : "bg-white/10",
                    )}
                  />
                )}
                <div
                  className={cn(
                    "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs",
                    isComplete &&
                      "border-sky-400/50 bg-sky-400/15 text-sky-400",
                    isCurrent &&
                      "border-sky-400 bg-sky-400/20 text-sky-400 sky-glow",
                    isPending &&
                      "border-frame/15 bg-frame/5 text-muted-foreground",
                  )}
                  aria-current={isCurrent ? "step" : undefined}
                  title={legendForPipelineStep(step.key)}
                >
                  {isComplete ? (
                    <Check className="h-3 w-3" aria-hidden />
                  ) : isCurrent ? (
                    <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
                  ) : (
                    <Circle className="h-2.5 w-2.5 opacity-40" aria-hidden />
                  )}
                </div>
                {idx < PIPELINE_STEPS.length - 1 && (
                  <div
                    className={cn(
                      "h-px flex-1",
                      idx < currentIdx ? "bg-sky-400/60" : "bg-white/10",
                    )}
                  />
                )}
              </div>
              <span
                className={cn(
                  "text-[10px] sm:text-xs truncate w-full text-center",
                  isCurrent
                    ? "text-sky-400 font-medium"
                    : isPending
                      ? "text-muted-foreground"
                      : "text-foreground/80",
                )}
              >
                {step.label}
              </span>
              {duration != null && duration > 0 && (
                <span className="text-[10px] font-mono text-muted-foreground">
                  {formatDurationSeconds(duration)}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/**
 * Renders the live progress timeline for a single job using SSE.
 */
export function LiveProgress({
  jobId,
  initialStatus,
  initialProgress,
  initialStage,
  initialStageDurations,
  initialTotalElapsedSecs,
}: LiveProgressProps) {
  const router = useRouter();
  const { push: toast } = useToastSafe();
  const finished = TERMINAL.has(initialStatus);

  const state = useJobProgress(jobId, { enabled: !finished });

  const liveEvent: ProgressEvent | null =
    "lastEvent" in state ? (state.lastEvent ?? null) : null;

  const stage = liveEvent?.stage ?? initialStage;
  const progress = liveEvent?.progress ?? initialProgress;
  const status =
    liveEvent?.status === "done"
      ? "done"
      : liveEvent?.status === "error"
        ? "error"
        : finished
          ? initialStatus
          : "processing";

  const streamNotice =
    state.stalled && !TERMINAL.has(status)
      ? "No progress updates for a few minutes — the worker may be stuck. You can cancel and retry, or wait a bit longer."
      : state.status === "reconnecting"
        ? "Reconnecting to progress stream…"
        : state.status === "polling"
          ? "Live stream unavailable — refreshing via API"
          : null;

  const rawMessage = liveEvent?.message ?? initialStage;
  const errorCode =
    liveEvent?.extra && typeof liveEvent.extra === "object"
      ? String((liveEvent.extra as Record<string, unknown>).code ?? "")
      : undefined;
  const message =
    status === "error"
      ? userFacingErrorMessage(rawMessage, errorCode || null, "Job failed.")
      : rawMessage;

  const totalElapsedBase =
    liveEvent?.total_elapsed_secs ?? initialTotalElapsedSecs ?? null;
  const etaBase = liveEvent?.eta_secs ?? null;
  const stageDurations: StageDurations = {
    ...(initialStageDurations ?? {}),
    ...(liveEvent?.stage_durations ?? {}),
  };

  const isRunning = status === "processing";
  const liveTotalElapsed = useLiveSeconds(totalElapsedBase, isRunning);
  const liveEta = useLiveSeconds(etaBase, isRunning && etaBase != null, "down");

  React.useEffect(() => {
    if (state.status === "done") {
      toast("Job complete", "Your clips are ready to download.");
      router.refresh();
    }
    if (state.status === "error") {
      const msg = "message" in state ? state.message : undefined;
      if (msg) toast("Job failed", userFacingErrorMessage(msg, null, "Job failed."));
    }
  }, [state, router, toast]);

  if (state.status === "error") {
    return (
      <div className="glossy-surface border-destructive/30 p-4 space-y-2">
        <div className="flex items-center gap-2">
          <XCircle className="h-4 w-4 text-destructive shrink-0" />
          <span className="text-sm font-medium text-destructive">
            Job failed
          </span>
        </div>
        <p className="text-xs text-destructive/80">
          {"message" in state
            ? userFacingErrorMessage(state.message, null, "Job failed.")
            : "Job failed."}
        </p>
      </div>
    );
  }

  const canonical = canonicalStage(stage);
  const lowConfidenceEta =
    progress < 0.35 || canonical === "ingest" || canonical === "transcribe";
  const etaLabel = formatEtaRemaining(liveEta, {
    lowConfidence: lowConfidenceEta && liveEta != null,
  });

  const ingestSubPct =
    canonical === "ingest" ? parseIngestSubProgress(message) : null;

  const icon =
    status === "done" ? (
      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
    ) : status === "error" ? (
      <XCircle className="h-4 w-4 text-destructive" />
    ) : (
      <Loader2 className="h-4 w-4 animate-spin text-sky-400" />
    );

  return (
    <div className="glossy-surface p-4 space-y-4">
      {streamNotice ? (
        <p className="text-xs text-amber-700 dark:text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded px-2 py-1.5">
          {streamNotice}
        </p>
      ) : null}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 min-w-0">
          {icon}
          <span className="text-sm font-medium truncate">{message}</span>
        </div>
        <LegendBadge
          className={statusColors[status] ?? statusColors.queued}
          tip={legendForStatus(status)}
          tipLabel="Job status help"
        >
          {status}
        </LegendBadge>
      </div>

      {(liveTotalElapsed != null || etaLabel) && (
        <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
          {liveTotalElapsed != null && (
            <LegendLabel
              tip={PROGRESS_LEGEND.elapsed}
              tipLabel="Elapsed time help"
              className="inline-flex items-center gap-1"
            >
              <span className="font-mono text-foreground">
                {formatDurationSeconds(liveTotalElapsed)}
              </span>{" "}
              since start
            </LegendLabel>
          )}
          {etaLabel && (
            <LegendLabel
              tip={PROGRESS_LEGEND.eta}
              tipLabel="ETA help"
              className="font-mono text-sky-400"
            >
              {etaLabel}
            </LegendLabel>
          )}
        </div>
      )}

      <PipelineStepper
        currentStage={stage}
        stageDurations={stageDurations}
        finished={status === "done"}
      />

      <div className="space-y-1">
        <span className="term-label">Progress</span>
        <Progress value={progress} />
      </div>

      {ingestSubPct != null && (
        <div className="space-y-1">
          <span className="term-label">Ingest</span>
          <Progress value={ingestSubPct / 100} />
          <div className="text-right text-xs font-mono text-muted-foreground">
            {ingestSubPct}%
          </div>
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <LegendLabel
          tip={legendForStage(stage)}
          tipLabel="Pipeline stage help"
          className="font-mono"
        >
          {stage}
        </LegendLabel>
        <span className="text-sky-400 font-medium font-mono">
          {(progress * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  );
}

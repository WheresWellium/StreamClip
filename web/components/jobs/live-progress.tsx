"use client";

import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { Progress } from "@/components/ui/form";
import { HelpTip } from "@/components/ui/help-tip";
import { LegendBadge } from "@/components/ui/legend-badge";
import { useJobProgress } from "@/lib/api/use-job-progress";
import { PROGRESS_LEGEND, legendForStage, legendForStatus } from "@/lib/help/legends";
import { statusColors } from "@/lib/utils/format";

interface LiveProgressProps {
  jobId: string;
  initialStatus: string;
  initialProgress: number;
  initialStage: string;
}

const TERMINAL = new Set(["done", "error", "cancelled"]);

/**
 * Renders the live progress timeline for a single job using SSE.
 * Server-renders the last-known state, then upgrades to live updates
 * on the client. When the job ends, refreshes the Server Component
 * tree so the clip grid reveals itself.
 */
export function LiveProgress({
  jobId,
  initialStatus,
  initialProgress,
  initialStage,
}: LiveProgressProps) {
  const router = useRouter();
  const finished = TERMINAL.has(initialStatus);

  const state = useJobProgress(jobId, { enabled: !finished });

  // When the SSE stream terminates, refresh server data so clips appear
  React.useEffect(() => {
    if (state.status === "done") {
      router.refresh();
    }
  }, [state.status, router]);

  if (state.status === "error") {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 space-y-2">
        <div className="flex items-center gap-2">
          <XCircle className="h-4 w-4 text-destructive shrink-0" />
          <span className="text-sm font-medium text-destructive">
            Progress stream disconnected
          </span>
        </div>
        <p className="text-xs text-destructive/80">{state.message}</p>
      </div>
    );
  }

  // Decide what to render: SSE live > initial server state
  const liveEvent =
    state.status === "open" || state.status === "done"
      ? state.lastEvent
      : null;

  const stage = liveEvent?.stage ?? initialStage;
  const message = liveEvent?.message ?? initialStage;
  const progress = liveEvent?.progress ?? initialProgress;
  const status =
    liveEvent?.status === "done"
      ? "done"
      : liveEvent?.status === "error"
        ? "error"
        : finished
          ? initialStatus
          : "processing";

  const icon =
    status === "done" ? (
      <CheckCircle2 className="h-4 w-4 text-green-500" />
    ) : status === "error" ? (
      <XCircle className="h-4 w-4 text-destructive" />
    ) : (
      <Loader2 className="h-4 w-4 animate-spin text-primary" />
    );

  return (
    <div className="rounded-lg border border-border/60 bg-card p-4 space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          {icon}
          <span className="text-sm font-medium truncate">{message}</span>
          <HelpTip content={PROGRESS_LEGEND.message} label="Progress message help" />
        </div>
        <LegendBadge
          className={statusColors[status] ?? statusColors.queued}
          tip={legendForStatus(status)}
          tipLabel="Job status help"
        >
          {status}
        </LegendBadge>
      </div>
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Progress</span>
          <HelpTip content={PROGRESS_LEGEND.bar} label="Progress bar help" />
        </div>
        <Progress value={progress} />
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1 font-mono">
          {stage}
          <HelpTip content={legendForStage(stage)} label="Pipeline stage help" />
        </span>
        <span>{(progress * 100).toFixed(0)}%</span>
      </div>
    </div>
  );
}

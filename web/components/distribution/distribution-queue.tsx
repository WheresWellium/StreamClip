"use client";

import { ExternalLink, Loader2, Pencil, RotateCcw, X } from "lucide-react";
import * as React from "react";

import {
  cancelPublishJobAction,
  retryPublishJobAction,
  updatePublishJobAction,
} from "@/lib/api/actions/distribution";
import { useToastSafe } from "@/components/providers/toast-provider";
import { usePublishProgress } from "@/hooks/use-publish-progress";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/form";
import { RelativeTime } from "@/components/ui/relative-time";
import type { PublishJob } from "@/lib/api/client";
import { cn } from "@/lib/utils/format";

type Tab = "queue" | "activity";

const QUEUE_STATUSES = new Set(["pending", "scheduled", "publishing"]);
const ACTIVITY_STATUSES = new Set(["published", "failed", "cancelled"]);

const PLATFORM_LABELS: Record<string, string> = {
  youtube_shorts: "YouTube Shorts",
  tiktok: "TikTok",
};

const STATUS_STYLES: Record<string, string> = {
  pending: "text-sky-400",
  scheduled: "text-violet-400",
  publishing: "text-amber-400",
  published: "text-emerald-400",
  failed: "text-destructive",
  cancelled: "text-muted-foreground",
};

type Props = {
  jobs: PublishJob[];
  hasPro: boolean;
  onRefresh?: () => void | Promise<void>;
};

function toDatetimeLocal(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

type PublishJobRowProps = {
  job: PublishJob;
  hasPro: boolean;
  busyId: string | null;
  editingId: string | null;
  editTitle: string;
  editScheduledAt: string;
  onStartEdit: (job: PublishJob) => void;
  onDiscardEdit: () => void;
  onSaveEdit: (job: PublishJob) => void;
  onRetry: (jobId: string) => void;
  onCancel: (jobId: string) => void;
  onEditTitleChange: (v: string) => void;
  onEditScheduledAtChange: (v: string) => void;
  onRefresh?: () => void | Promise<void>;
};

function PublishJobRow({
  job,
  hasPro,
  busyId,
  editingId,
  editTitle,
  editScheduledAt,
  onStartEdit,
  onDiscardEdit,
  onSaveEdit,
  onRetry,
  onCancel,
  onEditTitleChange,
  onEditScheduledAtChange,
  onRefresh,
}: PublishJobRowProps) {
  const { event: liveEvent, terminal } = usePublishProgress(
    job.status === "publishing" ? job.id : null,
  );

  React.useEffect(() => {
    if (terminal) void onRefresh?.();
  }, [terminal, onRefresh]);

  const platformLabel = PLATFORM_LABELS[job.platform] ?? job.platform;
  const statusClass = STATUS_STYLES[job.status] ?? "text-muted-foreground";
  const canCancel = job.status === "pending" || job.status === "scheduled";
  const canRetry = job.status === "failed";
  const canEdit = canCancel;
  const isEditing = editingId === job.id;
  const isBusy = busyId === job.id;
  const externalUrl = liveEvent?.external_url ?? job.external_url;

  return (
    <li className="glossy-surface rounded-lg border border-border/60 p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">
            {job.title || "Untitled clip"}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {platformLabel}
            {job.scheduled_at && job.status === "scheduled" && (
              <>
                {" · "}
                <RelativeTime iso={job.scheduled_at} />
              </>
            )}
            {job.published_at && job.status === "published" && (
              <>
                {" · "}
                <RelativeTime iso={job.published_at} />
              </>
            )}
          </p>
        </div>
        <span className={cn("text-xs capitalize shrink-0", statusClass)}>
          {job.status === "publishing" && (
            <Loader2 className="inline h-3 w-3 animate-spin mr-1" />
          )}
          {job.status}
        </span>
      </div>

      {job.error_message && job.status === "failed" && (
        <p className="text-xs text-destructive/90 line-clamp-2">
          {job.error_message}
        </p>
      )}

      {job.status === "publishing" && liveEvent && (
        <div className="space-y-1">
          <div className="h-1 w-full rounded-full bg-secondary overflow-hidden">
            <div
              className="h-full bg-amber-400/70 transition-[width]"
              style={{ width: `${Math.min(100, Math.round(liveEvent.progress * 100))}%` }}
            />
          </div>
          {liveEvent.message && (
            <p className="text-[10px] text-muted-foreground truncate">
              {liveEvent.message}
            </p>
          )}
        </div>
      )}

      {isEditing && (
        <div className="space-y-2 rounded-md border border-border/60 bg-background/60 p-2">
          <div className="space-y-1">
            <label
              className="text-[10px] text-muted-foreground"
              htmlFor={`pub-title-${job.id}`}
            >
              Title
            </label>
            <Input
              id={`pub-title-${job.id}`}
              className="h-8 text-xs"
              value={editTitle}
              maxLength={255}
              onChange={(e) => onEditTitleChange(e.target.value)}
            />
          </div>
          {job.status === "scheduled" && (
            <div className="space-y-1">
              <label
                className="text-[10px] text-muted-foreground"
                htmlFor={`pub-sched-${job.id}`}
              >
                Publish at
              </label>
              <Input
                id={`pub-sched-${job.id}`}
                className="h-8 text-xs"
                type="datetime-local"
                value={editScheduledAt}
                onChange={(e) => onEditScheduledAtChange(e.target.value)}
              />
            </div>
          )}
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              className="h-7 text-xs"
              disabled={isBusy}
              onClick={() => onSaveEdit(job)}
            >
              {isBusy ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                "Save"
              )}
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-muted-foreground"
              onClick={onDiscardEdit}
            >
              Discard
            </Button>
          </div>
        </div>
      )}

      <div className="flex items-center gap-2 flex-wrap">
        {externalUrl && (
          <a
            href={externalUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-emerald-400 hover:underline"
          >
            View post
            <ExternalLink className="h-3 w-3" />
          </a>
        )}
        {canRetry && hasPro && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            disabled={isBusy}
            onClick={() => onRetry(job.id)}
          >
            {isBusy ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <RotateCcw className="h-3 w-3" />
            )}
            Retry
          </Button>
        )}
        {canEdit && hasPro && !isEditing && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            disabled={isBusy}
            onClick={() => onStartEdit(job)}
          >
            <Pencil className="h-3 w-3" />
            Edit
          </Button>
        )}
        {canCancel && hasPro && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-7 text-xs text-muted-foreground"
            disabled={isBusy}
            onClick={() => onCancel(job.id)}
          >
            {isBusy ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <X className="h-3 w-3" />
            )}
            Cancel
          </Button>
        )}
      </div>
    </li>
  );
}

export function DistributionQueue({ jobs, hasPro, onRefresh }: Props) {
  const { push: toast } = useToastSafe();
  const [tab, setTab] = React.useState<Tab>("queue");
  const [busyId, setBusyId] = React.useState<string | null>(null);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [editTitle, setEditTitle] = React.useState("");
  const [editScheduledAt, setEditScheduledAt] = React.useState("");

  const queueJobs = jobs.filter((j) => QUEUE_STATUSES.has(j.status));
  const activityJobs = jobs.filter((j) => ACTIVITY_STATUSES.has(j.status));
  const visible = tab === "queue" ? queueJobs : activityJobs;

  async function handleRetry(jobId: string) {
    setBusyId(jobId);
    try {
      const result = await retryPublishJobAction(jobId);
      if (result.status === "ok") {
        toast("Retry queued", "Upload will restart shortly.");
        if (onRefresh) await onRefresh();
      } else {
        toast("Retry failed", result.message ?? "Could not retry.");
      }
    } finally {
      setBusyId(null);
    }
  }

  async function handleCancel(jobId: string) {
    setBusyId(jobId);
    try {
      const result = await cancelPublishJobAction(jobId);
      if (result.status === "ok") {
        toast("Cancelled", "Publish job removed from queue.");
        if (onRefresh) await onRefresh();
      } else {
        toast("Cancel failed", result.message ?? "Could not cancel.");
      }
    } finally {
      setBusyId(null);
    }
  }

  function startEdit(job: PublishJob) {
    setEditingId(job.id);
    setEditTitle(job.title || "");
    setEditScheduledAt(job.scheduled_at ? toDatetimeLocal(job.scheduled_at) : "");
  }

  async function handleSaveEdit(job: PublishJob) {
    setBusyId(job.id);
    try {
      const result = await updatePublishJobAction(job.id, {
        title: editTitle.trim() || undefined,
        scheduledAt:
          job.status === "scheduled" && editScheduledAt
            ? new Date(editScheduledAt).toISOString()
            : undefined,
      });
      if (result.status === "ok") {
        toast("Updated", "Publish job updated.");
        setEditingId(null);
        if (onRefresh) await onRefresh();
      } else {
        toast("Update failed", result.message ?? "Could not update.");
      }
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-4">
      <div role="tablist" className="flex rounded-md border border-border/60 overflow-hidden text-xs">
        {(
          [
            { id: "queue" as const, label: "Queue", count: queueJobs.length },
            { id: "activity" as const, label: "Activity", count: activityJobs.length },
          ] as const
        ).map(({ id, label, count }) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={cn(
              "flex-1 px-3 py-2 min-h-[44px] font-medium",
              tab === id ? "bg-sky-600/25 text-sky-100" : "text-muted-foreground",
            )}
          >
            {label}
            {count > 0 && (
              <span className="ml-1.5 text-[10px] opacity-70">({count})</span>
            )}
          </button>
        ))}
      </div>

      {!hasPro && (
        <p className="text-xs text-amber-400/90">
          Pro license required to publish. Queue shows jobs from your account.
        </p>
      )}

      {visible.length === 0 ? (
        <p className="text-sm text-muted-foreground py-6 text-center">
          {tab === "queue"
            ? "No scheduled or in-progress publishes."
            : "No publish history yet."}
        </p>
      ) : (
        <ul className="space-y-2">
          {visible.map((job) => (
            <PublishJobRow
              key={job.id}
              job={job}
              hasPro={hasPro}
              busyId={busyId}
              editingId={editingId}
              editTitle={editTitle}
              editScheduledAt={editScheduledAt}
              onStartEdit={startEdit}
              onDiscardEdit={() => setEditingId(null)}
              onSaveEdit={(j) => void handleSaveEdit(j)}
              onRetry={(id) => void handleRetry(id)}
              onCancel={(id) => void handleCancel(id)}
              onEditTitleChange={setEditTitle}
              onEditScheduledAtChange={setEditScheduledAt}
              onRefresh={onRefresh}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

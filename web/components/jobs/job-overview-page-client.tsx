"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { CancelJobButton } from "@/components/jobs/cancel-job-button";
import { EditableJobTitle } from "@/components/jobs/editable-job-title";
import { LiveClipFeed } from "@/components/jobs/live-clip-feed";
import { LiveProgress } from "@/components/jobs/live-progress";
import { CollapsibleSection } from "@/components/ui/collapsible-section";
import { LegendBadge } from "@/components/ui/legend-badge";
import { RelativeTime } from "@/components/ui/relative-time";
import { Button } from "@/components/ui/button";
import { legendForStatus } from "@/lib/help/legends";
import {
  isJobNotFound,
  loadJobPageContext,
  type JobPageContext,
} from "@/lib/jobs/load-job-page-client";
import {
  formatDuration,
  statusColors,
} from "@/lib/utils/format";
import { Film, ArrowRight } from "lucide-react";

export function JobOverviewPageClient() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const jobId = params.id;
  const [ctx, setCtx] = useState<JobPageContext | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void loadJobPageContext(jobId)
      .then((data) => {
        if (!cancelled) setCtx(data);
      })
      .catch((err) => {
        if (cancelled) return;
        if (isJobNotFound(err)) {
          router.replace("/jobs");
          return;
        }
        setError(err instanceof Error ? err.message : "Failed to load job");
      });
    return () => {
      cancelled = true;
    };
  }, [jobId, router]);

  if (error) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
        {error}
      </div>
    );
  }

  if (!ctx) {
    return (
      <div className="mx-auto max-w-3xl py-12 text-center text-sm text-muted-foreground">
        Loading job…
      </div>
    );
  }

  const { job } = ctx;
  const clipCount = job.clips.length;
  const readyClips = job.clips.filter((c) => c.status === "done").length;

  return (
    <div className="mx-auto max-w-3xl space-y-6 animate-fade-in">
      <Link
        href="/jobs"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        ← All jobs
      </Link>

      <div className="space-y-2">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <EditableJobTitle
            jobId={job.id}
            displayTitle={job.display_title}
            sourceTitle={job.source_title}
            variant="header"
          />
          <div className="flex items-center gap-2">
            <LegendBadge
              className={statusColors[job.status] ?? statusColors.queued}
              tip={legendForStatus(job.status)}
              tipLabel="Job status help"
            >
              {job.status}
            </LegendBadge>
            <CancelJobButton jobId={job.id} status={job.status} />
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          <RelativeTime iso={job.created_at} />
          {job.source_duration_secs ? (
            <> · {formatDuration(job.source_duration_secs)} source</>
          ) : null}
          {clipCount > 0 ? <> · {clipCount} clips</> : null}
        </p>
      </div>

      <LiveProgress
        jobId={job.id}
        initialStatus={job.status}
        initialProgress={job.progress}
        initialStage={job.current_stage}
      />

      <LiveClipFeed
        jobId={job.id}
        jobStatus={job.status}
        initialClipCount={clipCount}
        showReviewLink
      />

      {job.status === "error" && job.error_message && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm">
          <p className="font-medium text-destructive">{job.error_code}</p>
          <p className="text-destructive/80 mt-0.5">{job.error_message}</p>
        </div>
      )}

      {clipCount > 0 ? (
        <div className="rounded-lg border border-sky-400/30 bg-sky-400/5 p-5 flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-sky-400/15 text-sky-400">
            <Film className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0 space-y-1">
            <p className="font-medium">
              {readyClips === clipCount
                ? `${clipCount} clips ready to review`
                : `${readyClips} of ${clipCount} clips rendered`}
            </p>
            <p className="text-sm text-muted-foreground">
              Approve, edit boundaries, and publish from the clips workspace — kept
              separate so this page stays focused on pipeline status.
            </p>
          </div>
          <Button asChild size="lg" className="shrink-0">
            <Link href={`/jobs/${job.id}/clips`}>
              Review clips
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      ) : job.status === "done" ? (
        <div className="rounded-lg border border-border/60 bg-card p-8 text-center text-sm text-muted-foreground">
          No clips could be rendered. The source may be empty or corrupt — check the
          error details above if any.
        </div>
      ) : (
        <div className="rounded-lg border border-border/60 bg-card/50 px-4 py-6 text-sm text-muted-foreground text-center">
          Clips appear here when the pipeline finishes highlight detection and rendering.
        </div>
      )}

      <CollapsibleSection
        title="Job details"
        summary={job.source_url ? job.source_url.replace(/^https?:\/\//, "") : job.id}
      >
        <dl className="grid gap-3 text-sm">
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">Job ID</dt>
            <dd className="font-mono text-xs mt-0.5 break-all">{job.id}</dd>
          </div>
          {job.source_url && (
            <div>
              <dt className="text-xs uppercase tracking-wide text-muted-foreground">Source</dt>
              <dd className="mt-0.5">
                <a
                  href={job.source_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="text-sky-400 hover:underline break-all"
                >
                  {job.source_url}
                </a>
              </dd>
            </div>
          )}
          {job.content_profile && (
            <div>
              <dt className="text-xs uppercase tracking-wide text-muted-foreground">Content profile</dt>
              <dd className="mt-0.5 capitalize">{job.content_profile.replace(/_/g, " ")}</dd>
            </div>
          )}
          {job.aspect_ratio && (
            <div>
              <dt className="text-xs uppercase tracking-wide text-muted-foreground">Aspect ratio</dt>
              <dd className="mt-0.5">{job.aspect_ratio}</dd>
            </div>
          )}
        </dl>
      </CollapsibleSection>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ClipCard } from "@/components/clips/clip-card";
import { HeuristicViralityBanner } from "@/components/clips/heuristic-virality-banner";
import { JobClipsToolbar } from "@/components/clips/job-clips-toolbar";
import { SpliceClipsToolbar } from "@/components/clips/splice-clips-toolbar";
import { LiveClipFeed } from "@/components/jobs/live-clip-feed";
import { LegendBadge } from "@/components/ui/legend-badge";
import type { ClipOut } from "@/lib/api/types";
import { legendForStatus } from "@/lib/help/legends";
import { jobOverviewPath } from "@/lib/jobs/job-route-id";
import {
  isJobNotFound,
  loadJobPageContext,
  type JobPageContext,
} from "@/lib/jobs/load-job-page-client";
import { getEffectiveJobTitle } from "@/lib/jobs/title";
import { useResolvedJobId } from "@/lib/jobs/use-resolved-job-id";
import { statusColors } from "@/lib/utils/format";

export function JobClipsPageClient() {
  const { jobId, ready } = useResolvedJobId();
  const [ctx, setCtx] = useState<JobPageContext | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    if (!ready) return;
    if (!jobId) {
      setMissing(true);
      setCtx(null);
      return;
    }
    let cancelled = false;
    setMissing(false);
    setError(null);
    void loadJobPageContext(jobId)
      .then((data) => {
        if (!cancelled) setCtx(data);
      })
      .catch((err) => {
        if (cancelled) return;
        if (isJobNotFound(err)) {
          setMissing(true);
          return;
        }
        setError(err instanceof Error ? err.message : "Failed to load job");
      });
    return () => {
      cancelled = true;
    };
  }, [jobId, ready]);

  if (missing) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center space-y-4">
        <h1 className="text-3xl font-semibold">Job not found</h1>
        <p className="text-muted-foreground max-w-sm">
          We couldn&apos;t find this job. It may have been deleted or you may not have
          access.
        </p>
        <Link
          href="/jobs/"
          className="text-sky-400 hover:underline text-sm"
        >
          Back to jobs
        </Link>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
        {error}
      </div>
    );
  }

  if (!ready || !ctx) {
    return (
      <div className="py-12 text-center text-sm text-muted-foreground">Loading clips…</div>
    );
  }

  const {
    job,
    captionStyleOptions,
    reframePresetOptions,
    aspectRatioCatalog,
    hasDistribution,
  } = ctx;

  const approvedClipCount = (job.clips as ClipOut[]).filter(
    (c) => c.approval_status === "approved" && c.status === "done",
  ).length;

  const jobTitle = getEffectiveJobTitle(job);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <Link
          href="/jobs/"
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          All jobs
        </Link>
        <span className="text-muted-foreground/50" aria-hidden>
          /
        </span>
        <a
          href={jobOverviewPath(job.id)}
          className="text-muted-foreground hover:text-foreground transition-colors truncate max-w-[200px]"
        >
          {jobTitle}
        </a>
        <span className="text-muted-foreground/50" aria-hidden>
          /
        </span>
        <span className="text-foreground font-medium">Clips</span>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">
            Clips
            <span className="text-muted-foreground font-normal">
              {" "}
              · {jobTitle}
            </span>
          </h1>
          <p className="text-sm text-muted-foreground">
            {job.clips.length} clips · approve and publish when ready
          </p>
        </div>
        <LegendBadge
          className={statusColors[job.status] ?? statusColors.queued}
          tip={legendForStatus(job.status)}
          tipLabel="Job status help"
        >
          {job.status}
        </LegendBadge>
      </div>

      <LiveClipFeed
        jobId={job.id}
        jobStatus={job.status}
        initialClipCount={job.clips.length}
      />

      <HeuristicViralityBanner clips={job.clips} />

      {job.clips.length > 0 ? (
        <>
          <JobClipsToolbar
            jobId={job.id}
            clipCount={job.clips.length}
            approvedClipCount={approvedClipCount}
            jobStatus={job.status}
            contentProfile={job.content_profile}
            hasDistribution={hasDistribution}
          />
          <SpliceClipsToolbar
            jobId={job.id}
            clips={job.clips}
            jobDone={job.status === "done" || job.status === "error"}
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {job.clips.map((clip) => (
              <ClipCard
                key={clip.id}
                clip={clip}
                jobId={job.id}
                jobDone={job.status === "done" || job.status === "error"}
                sourceDurationSecs={job.source_duration_secs}
                captionStyleOptions={captionStyleOptions}
                reframePresetOptions={reframePresetOptions}
                jobAspectRatio={job.aspect_ratio}
                aspectRatioCatalog={aspectRatioCatalog}
              />
            ))}
          </div>
        </>
      ) : (
        <div className="rounded-lg border border-border/60 bg-card p-8 text-center text-sm text-muted-foreground">
          No clips yet.{" "}
          <a href={jobOverviewPath(job.id)} className="text-sky-400 hover:underline">
            Return to job status
          </a>{" "}
          to watch pipeline progress.
        </div>
      )}
    </div>
  );
}

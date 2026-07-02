import { BackToJobsLink } from "@/components/jobs/back-link";
import { CancelJobButton } from "@/components/jobs/cancel-job-button";
import { ClipCard } from "@/components/clips/clip-card";
import { JobClipsToolbar } from "@/components/clips/job-clips-toolbar";
import { SpliceClipsToolbar } from "@/components/clips/splice-clips-toolbar";
import { LiveProgress } from "@/components/jobs/live-progress";
import { LegendBadge } from "@/components/ui/legend-badge";
import { RelativeTime } from "@/components/ui/relative-time";
import { legendForStatus } from "@/lib/help/legends";
import { ApiClientError, jobsApi, metaApi } from "@/lib/api/client";
import type { ClipOut } from "@/lib/api/types";
import { getAccessToken } from "@/lib/auth/session";
import { hasDistributionAccess } from "@/lib/distribution/access";
import { normalizeStreamClipMeta } from "@/lib/normalize-meta";
import {
  formatDuration,
  statusColors,
} from "@/lib/utils/format";
import { notFound } from "next/navigation";

interface JobPageProps {
  params: Promise<{ id: string }>;
}

export default async function JobPage({ params }: JobPageProps) {
  const { id } = await params;

  let job;
  let captionStyleOptions = normalizeStreamClipMeta({}).caption_styles;
  let reframePresetOptions = normalizeStreamClipMeta({}).reframe_presets;
  let hasDistribution = false;
  try {
    const token = await getAccessToken();
    hasDistribution = token ? await hasDistributionAccess(token) : false;
    job = await jobsApi.get(id, token);
    const rawMeta = await metaApi.meta();
    const meta = normalizeStreamClipMeta(rawMeta as Record<string, unknown>);
    captionStyleOptions = meta.caption_styles;
    reframePresetOptions = meta.reframe_presets;
  } catch (err) {
    if (err instanceof ApiClientError && err.status === 404) {
      notFound();
    }
    throw err;
  }

  const approvedClipCount = (job.clips as ClipOut[]).filter(
    (c) => c.approval_status === "approved" && c.status === "done",
  ).length;

  return (
    <div className="space-y-6 animate-fade-in">
      <BackToJobsLink />

      <div className="space-y-2">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <h1 className="text-2xl font-semibold tracking-tight">
            {job.source_title ?? "Untitled job"}
          </h1>
          <LegendBadge
            className={statusColors[job.status] ?? statusColors.queued}
            tip={legendForStatus(job.status)}
            tipLabel="Job status help"
          >
            {job.status}
          </LegendBadge>
          <CancelJobButton jobId={job.id} status={job.status} />
        </div>
        <div className="flex items-center gap-3 text-sm text-muted-foreground flex-wrap">
          <span className="font-mono text-xs">{job.id}</span>
          <span aria-hidden>/</span>
          <span><RelativeTime iso={job.created_at} /></span>
          {job.source_duration_secs && (
            <>
              <span>·</span>
              <span>{formatDuration(job.source_duration_secs)} source</span>
            </>
          )}
          {job.source_url && (
            <>
              <span>·</span>
              <a
                href={job.source_url}
                target="_blank"
                rel="noreferrer noopener"
                className="hover:text-foreground transition-colors truncate max-w-xs"
              >
                {job.source_url}
              </a>
            </>
          )}
        </div>
      </div>

      <LiveProgress
        jobId={job.id}
        initialStatus={job.status}
        initialProgress={job.progress}
        initialStage={job.current_stage}
      />

      {job.status === "error" && job.error_message && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm">
          <p className="font-medium text-destructive">{job.error_code}</p>
          <p className="text-destructive/80 mt-0.5">{job.error_message}</p>
        </div>
      )}

      {job.clips.length > 0 ? (
        <div>
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
            jobDone={job.status === "done"}
          />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {job.clips.map((clip) => (
              <ClipCard
                key={clip.id}
                clip={clip}
                jobId={job.id}
                jobDone={job.status === "done"}
                sourceDurationSecs={job.source_duration_secs}
                captionStyleOptions={captionStyleOptions}
                reframePresetOptions={reframePresetOptions}
                jobAspectRatio={job.aspect_ratio}
              />
            ))}
          </div>
        </div>
      ) : job.status === "done" ? (
        <div className="rounded-lg border border-border/60 bg-card p-8 text-center text-sm text-muted-foreground">
          No clips could be rendered. The source may be empty, corrupt, or the
          pipeline encountered an error — check the job status for details.
        </div>
      ) : null}
    </div>
  );
}

export const dynamic = "force-dynamic";

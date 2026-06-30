import { BackToJobsLink } from "@/components/jobs/back-link";
import { CancelJobButton } from "@/components/jobs/cancel-job-button";
import { ClipCard } from "@/components/clips/clip-card";
import { JobClipsToolbar } from "@/components/clips/job-clips-toolbar";
import { LiveProgress } from "@/components/jobs/live-progress";
import { HelpTip } from "@/components/ui/help-tip";
import { LegendBadge } from "@/components/ui/legend-badge";
import { legendForStatus } from "@/lib/help/legends";
import { ApiClientError, jobsApi } from "@/lib/api/client";
import { getAccessToken } from "@/lib/auth/session";
import {
  formatDuration,
  formatRelativeTime,
  statusColors,
} from "@/lib/utils/format";
import { notFound } from "next/navigation";

interface JobPageProps {
  params: Promise<{ id: string }>;
}

export default async function JobPage({ params }: JobPageProps) {
  const { id } = await params;

  let job;
  try {
    const token = await getAccessToken();
    job = await jobsApi.get(id, token);
  } catch (err) {
    if (err instanceof ApiClientError && err.status === 404) {
      notFound();
    }
    throw err;
  }

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
          <HelpTip content="Unique job identifier for this pipeline run." label="Job ID help" />
          <span>·</span>
          <span>{formatRelativeTime(job.created_at)}</span>
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
            jobStatus={job.status}
            contentProfile={job.content_profile}
          />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {job.clips.map((clip) => (
              <ClipCard
                key={clip.id}
                clip={clip}
                jobId={job.id}
                jobDone={job.status === "done"}
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

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ClipCard } from "@/components/clips/clip-card";
import { LiveProgress } from "@/components/jobs/live-progress";
import { Badge } from "@/components/ui/form";
import { ApiClientError, jobsApi } from "@/lib/api/client";
import {
  formatDuration,
  formatRelativeTime,
  statusColors,
} from "@/lib/utils/format";

interface JobPageProps {
  params: Promise<{ id: string }>;
}

export default async function JobPage({ params }: JobPageProps) {
  const { id } = await params;

  let job;
  try {
    job = await jobsApi.get(id);
  } catch (err) {
    if (err instanceof ApiClientError && err.status === 404) {
      notFound();
    }
    throw err;
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        All jobs
      </Link>

      <div className="space-y-2">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <h1 className="text-2xl font-semibold tracking-tight">
            {job.source_title ?? "Untitled job"}
          </h1>
          <Badge className={statusColors[job.status] ?? statusColors.queued}>
            {job.status}
          </Badge>
        </div>
        <div className="flex items-center gap-3 text-sm text-muted-foreground flex-wrap">
          <span className="font-mono text-xs">{job.id}</span>
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
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="text-lg font-medium">
              {job.clips.length} clip{job.clips.length === 1 ? "" : "s"}
            </h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {job.clips.map((clip) => (
              <ClipCard key={clip.id} clip={clip} />
            ))}
          </div>
        </div>
      ) : job.status === "done" ? (
        <div className="rounded-lg border border-border/60 bg-card p-8 text-center text-sm text-muted-foreground">
          No clips were generated for this video. The source may have been too
          short, too quiet, or below the virality threshold.
        </div>
      ) : null}
    </div>
  );
}

export const dynamic = "force-dynamic";

import Link from "next/link";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge, Progress } from "@/components/ui/form";
import { jobsApi } from "@/lib/api/client";
import {
  formatDuration,
  formatRelativeTime,
  statusColors,
} from "@/lib/utils/format";

/**
 * Server Component — fetches the job list on the server and renders the
 * static HTML. The user gets paint instantly; no client-side data fetch
 * waterfall. Cache is tagged so Server Actions can invalidate it.
 */
export async function JobsList() {
  let jobs;
  try {
    const data = await jobsApi.list(50, 0);
    jobs = data.jobs;
  } catch (err) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent jobs</CardTitle>
          <CardDescription className="text-destructive">
            {err instanceof Error ? err.message : "Failed to load jobs"}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (jobs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent jobs</CardTitle>
          <CardDescription>
            No jobs yet — paste a URL above to create your first.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent jobs</CardTitle>
        <CardDescription>
          {jobs.length} {jobs.length === 1 ? "job" : "jobs"}
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-border/60">
          {jobs.map((job) => (
            <Link
              key={job.id}
              href={`/jobs/${job.id}`}
              className="group flex items-center gap-4 px-6 py-3 hover:bg-secondary/40 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <p className="text-sm font-medium truncate">
                    {job.source_title ?? "Untitled job"}
                  </p>
                  <Badge
                    className={
                      statusColors[job.status] ?? statusColors.queued
                    }
                  >
                    {job.status}
                  </Badge>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{formatRelativeTime(job.created_at)}</span>
                  <span>·</span>
                  <span>{formatDuration(job.source_duration_secs)}</span>
                  {job.clip_count > 0 && (
                    <>
                      <span>·</span>
                      <span>{job.clip_count} clips</span>
                    </>
                  )}
                </div>
              </div>
              {job.status !== "done" &&
                job.status !== "error" &&
                job.status !== "cancelled" && (
                  <div className="w-24 shrink-0">
                    <Progress value={job.progress} />
                  </div>
                )}
              <span className="text-muted-foreground group-hover:text-foreground transition-colors text-xs font-mono">
                {job.id.slice(0, 8)}
              </span>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function JobsListSkeleton() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent jobs</CardTitle>
        <CardDescription className="text-muted-foreground/60">
          Loading…
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-border/60">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="px-6 py-3 flex items-center gap-4">
              <div className="flex-1 space-y-2">
                <div className="h-4 w-2/3 skeleton rounded" />
                <div className="h-3 w-1/3 skeleton rounded" />
              </div>
              <div className="h-2 w-24 skeleton rounded" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

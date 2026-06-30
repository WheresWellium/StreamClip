import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { SectionLegend } from "@/components/ui/section-legend";
import { JobListRow } from "@/components/jobs/job-list-row";
import { jobsApi } from "@/lib/api/client";
import type { JobListItem } from "@/lib/api/types";
import { getAccessToken } from "@/lib/auth/session";

/**
 * Server Component — fetches the job list on the server and renders the
 * static HTML. The user gets paint instantly; no client-side data fetch
 * waterfall. Cache is tagged so Server Actions can invalidate it.
 */
export async function JobsList() {
  let jobs: JobListItem[];
  try {
    const token = await getAccessToken();
    const data = await jobsApi.list(50, 0, token);
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
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <CardTitle>Recent jobs</CardTitle>
          <SectionLegend
            title="List"
            tip="Pipeline runs newest first. Hover any status badge or metric for what it means."
            className="normal-case tracking-normal"
          />
        </div>
        <CardDescription>
          {jobs.length} {jobs.length === 1 ? "job" : "jobs"}
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-border/60">
          {jobs.map((job) => (
            <JobListRow key={job.id} job={job} />
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

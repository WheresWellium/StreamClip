import { Suspense } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { SectionLegend } from "@/components/ui/section-legend";
import { JobListRow } from "@/components/jobs/job-list-row";
import { JobsListFilters } from "@/components/jobs/jobs-list-filters";
import { jobsApi } from "@/lib/api/client";
import type { JobListItem } from "@/lib/api/types";
import { getAccessToken, getDeviceId } from "@/lib/auth/session";

type Props = {
  searchParams?: { search?: string; status?: string };
};

export async function JobsList({ searchParams }: Props) {
  let jobs: JobListItem[];
  try {
    const token = await getAccessToken();
    const deviceId = await getDeviceId();
    const data = await jobsApi.list(50, 0, token, {
      search: searchParams?.search,
      status: searchParams?.status,
    }, deviceId);
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

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <CardTitle>Recent jobs</CardTitle>
          <SectionLegend
            title="List"
            tip="Pipeline runs newest first. Filter by status or search."
            className="normal-case tracking-normal"
          />
        </div>
        <CardDescription>
          {jobs.length} {jobs.length === 1 ? "job" : "jobs"}
        </CardDescription>
      </CardHeader>
      <Suspense fallback={null}>
        <JobsListFilters />
      </Suspense>
      <CardContent className="p-0">
        {jobs.length === 0 ? (
          <div className="px-6 py-8 text-center space-y-2">
            <p className="text-sm text-muted-foreground">No jobs yet.</p>
            <p className="text-xs text-muted-foreground/80">
              Paste a stream URL above or upload a video to create your first clip.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {jobs.map((job) => (
              <JobListRow key={job.id} job={job} />
            ))}
          </div>
        )}
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

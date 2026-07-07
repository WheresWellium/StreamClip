"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { SectionLegend } from "@/components/ui/section-legend";
import { JobsListFilters } from "@/components/jobs/jobs-list-filters";
import { JobsListView } from "@/components/jobs/jobs-list-view";
import { jobsApi } from "@/lib/api/client";
import type { JobListItem } from "@/lib/api/types";
import {
  getClientAccessToken,
  getClientDeviceId,
} from "@/lib/auth/client-session";

export function JobsList() {
  const searchParams = useSearchParams();
  const search = searchParams.get("search") ?? undefined;
  const status = searchParams.get("status") ?? undefined;
  const [jobs, setJobs] = useState<JobListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const token = getClientAccessToken();
    const deviceId = getClientDeviceId();
    void jobsApi
      .list(50, 0, token, { search, status }, deviceId)
      .then((data) => {
        if (!cancelled) setJobs(data.jobs);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load jobs");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [search, status]);

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent jobs</CardTitle>
          <CardDescription className="text-destructive">{error}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (jobs === null) {
    return <JobsListSkeleton />;
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
          Pipeline runs newest first. Open a job for progress, then review clips when done.
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
              <Link href="/jobs/new" className="text-sky-400 hover:underline">
                Create a job
              </Link>{" "}
              from a URL or upload to get started.
            </p>
          </div>
        ) : (
          <JobsListView jobs={jobs} />
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

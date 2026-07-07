"use client";

import * as React from "react";

import { JobCard } from "@/components/jobs/job-card";
import { JobListRow } from "@/components/jobs/job-list-row";
import { ViewModeToggle } from "@/components/ui/view-mode-toggle";
import type { JobListItem } from "@/lib/api/types";
import {
  JOBS_VIEW_STORAGE_KEY,
  readViewMode,
  writeViewMode,
  type ViewMode,
} from "@/lib/view-mode";

export function JobsListView({ jobs }: { jobs: JobListItem[] }) {
  const [mode, setMode] = React.useState<ViewMode>("list");
  const [hydrated, setHydrated] = React.useState(false);

  React.useEffect(() => {
    setMode(readViewMode(JOBS_VIEW_STORAGE_KEY, "list"));
    setHydrated(true);
  }, []);

  const handleModeChange = (next: ViewMode) => {
    setMode(next);
    writeViewMode(JOBS_VIEW_STORAGE_KEY, next);
  };

  return (
    <>
      <div className="flex justify-end px-6 pb-3">
        {hydrated ? (
          <ViewModeToggle mode={mode} onChange={handleModeChange} />
        ) : (
          <div className="h-8 w-28 skeleton rounded-sm" />
        )}
      </div>
      {mode === "card" ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 px-6 pb-6">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      ) : (
        <div className="divide-y divide-white/5">
          {jobs.map((job) => (
            <JobListRow key={job.id} job={job} />
          ))}
        </div>
      )}
    </>
  );
}

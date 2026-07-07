import Link from "next/link";
import { Plus } from "lucide-react";
import { Suspense } from "react";

import { JobsList, JobsListSkeleton } from "@/components/jobs/jobs-list";
import { Button } from "@/components/ui/button";

export default function JobsPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Jobs</h1>
          <p className="text-sm text-muted-foreground max-w-lg">
            Pipeline runs for each source video. Open a job to track progress, then
            review clips when rendering finishes.
          </p>
        </div>
        <Button asChild>
          <Link href="/jobs/new">
            <Plus className="h-4 w-4" />
            New job
          </Link>
        </Button>
      </div>

      <Suspense fallback={<JobsListSkeleton />}>
        <JobsList />
      </Suspense>
    </div>
  );
}

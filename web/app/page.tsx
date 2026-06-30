import { Suspense } from "react";

import { CreateJobForm } from "@/components/jobs/create-job-form";
import { JobsList, JobsListSkeleton } from "@/components/jobs/jobs-list";

export default function HomePage() {
  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">StreamClip</h1>
        <p className="text-muted-foreground mt-1">
          Turn streams into vertical clips with subject tracking, animated
          captions, and meme overlays.
        </p>
      </div>

      <CreateJobForm />

      <Suspense fallback={<JobsListSkeleton />}>
        <JobsList />
      </Suspense>
    </div>
  );
}

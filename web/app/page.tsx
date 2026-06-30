import { Suspense } from "react";

import { AuthPanel } from "@/components/auth/auth-panel";
import { CreateJobForm } from "@/components/jobs/create-job-form";
import { JobsList, JobsListSkeleton } from "@/components/jobs/jobs-list";
import { getAccessToken } from "@/lib/auth/session";

export default async function HomePage() {
  const token = await getAccessToken();

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">StreamClip</h1>
        <p className="text-muted-foreground mt-1">
          Turn streams into vertical clips with subject tracking, animated
          captions, and meme overlays.
        </p>
      </div>

      <AuthPanel isAuthenticated={!!token} />

      <CreateJobForm />

      <Suspense fallback={<JobsListSkeleton />}>
        <JobsList />
      </Suspense>
    </div>
  );
}

import { JobClipsPageClient } from "@/components/jobs/job-clips-page-client";

export async function generateStaticParams() {
  return [{ id: "_" }];
}

export default function JobClipsPage() {
  return <JobClipsPageClient />;
}

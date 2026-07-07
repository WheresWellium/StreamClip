import { JobOverviewPageClient } from "@/components/jobs/job-overview-page-client";

export async function generateStaticParams() {
  return [{ id: "_" }];
}

export default function JobOverviewPage() {
  return <JobOverviewPageClient />;
}

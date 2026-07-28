import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center space-y-4">
      <h1 className="text-3xl font-semibold">Job not found</h1>
      <p className="text-muted-foreground max-w-sm">
        We couldn&apos;t find this job. It may have been deleted or you may not have
        access.
      </p>
      <Button asChild>
        <Link href="/jobs">Back to jobs</Link>
      </Button>
    </div>
  );
}

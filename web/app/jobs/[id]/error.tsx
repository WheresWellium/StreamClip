"use client";

import { useRouter } from "next/navigation";
import * as React from "react";

import { BugReportDialog } from "@/components/support/bug-report-dialog";
import { Button } from "@/components/ui/button";
import { help } from "@/lib/help/legends";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const router = useRouter();
  const [reportOpen, setReportOpen] = React.useState(false);

  React.useEffect(() => {
    // Keep digest for support; avoid crashing the boundary again.
    console.error("job_detail_error_boundary", {
      message: error?.message,
      digest: error?.digest,
    });
  }, [error]);

  const onRefresh = () => {
    reset();
    router.refresh();
  };

  return (
    <div className="flex flex-col items-center justify-center py-24 text-center space-y-4">
      <h1 className="text-2xl font-semibold">Something went wrong</h1>
      <p className="text-muted-foreground max-w-md text-sm">{help.errors.generic}</p>
      <p className="text-muted-foreground/80 max-w-md text-xs">
        {help.errors.jobDetail}
      </p>
      {error?.digest ? (
        <p className="text-muted-foreground/60 max-w-md text-[11px] font-mono">
          ref: {error.digest}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Button onClick={onRefresh}>Refresh</Button>
        <Button variant="outline" onClick={() => setReportOpen(true)}>
          Report a bug
        </Button>
      </div>
      <BugReportDialog
        open={reportOpen}
        onOpenChange={setReportOpen}
        defaultCategories={["ui"]}
        defaultSeverity="high"
        defaultMessage={
          [
            error?.message?.trim() || "Job page crashed after pipeline completed.",
            error?.digest ? `digest ${error.digest}` : null,
          ]
            .filter(Boolean)
            .join(" — ")
        }
      />
    </div>
  );
}

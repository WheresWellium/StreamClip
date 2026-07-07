"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { XCircle } from "lucide-react";

import { cancelJobAction } from "@/lib/api/actions/jobs";
import { Button } from "@/components/ui/button";

export function CancelJobButton({
  jobId,
  status,
}: {
  jobId: string;
  status: string;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const cancellable = ["queued", "ingesting", "transcribing", "detecting", "processing"].includes(
    status,
  );

  if (!cancellable) return null;

  return (
    <Button
      variant="outline"
      size="sm"
      disabled={pending}
      tooltip="Stop the pipeline and mark this job cancelled."
      onClick={() =>
        startTransition(async () => {
          await cancelJobAction(jobId);
          router.refresh();
        })
      }
    >
      <XCircle className="h-3.5 w-3.5" />
      {pending ? "Cancelling…" : "Cancel job"}
    </Button>
  );
}

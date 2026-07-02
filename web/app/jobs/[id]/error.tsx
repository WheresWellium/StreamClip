"use client";

import { Button } from "@/components/ui/button";
import { help } from "@/lib/help/legends";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center space-y-4">
      <h1 className="text-2xl font-semibold">Something went wrong</h1>
      <p className="text-muted-foreground max-w-md text-sm">{error.message}</p>
      <p className="text-muted-foreground/80 max-w-md text-xs">
        {help.errors.jobDetail}
      </p>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}

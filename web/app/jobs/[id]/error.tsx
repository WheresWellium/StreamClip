"use client";

import { Button } from "@/components/ui/button";
import { HelpTip } from "@/components/ui/help-tip";
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
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-semibold">Something went wrong</h1>
        <HelpTip content={help.errors.jobDetail} />
      </div>
      <p className="text-muted-foreground max-w-md text-sm">{error.message}</p>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}

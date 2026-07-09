"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { help } from "@/lib/help/legends";

export default function GlobalRouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center py-24 text-center space-y-4 px-4">
      <h1 className="text-2xl font-semibold">Something went wrong</h1>
      <p className="text-muted-foreground max-w-md text-sm">
        {help.errors.generic}
      </p>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}

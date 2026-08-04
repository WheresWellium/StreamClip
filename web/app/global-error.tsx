"use client";

import { useEffect } from "react";

import { formatGlobalErrorDetail } from "@/lib/errors/global-error-detail";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("qclip_global_error", {
      message: error.message,
      digest: error.digest,
      stack: error.stack,
    });
  }, [error]);

  const detail = formatGlobalErrorDetail(error);

  return (
    <html lang="en">
      <body className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-8">
        <h1 className="text-xl font-semibold mb-2">qClip hit an error</h1>
        <p className="text-sm text-muted-foreground max-w-md text-center mb-2">
          Refresh the page or restart the app. If this keeps happening, use Report a bug
          from the header.
        </p>
        {detail ? (
          <p
            className="text-xs text-muted-foreground/80 max-w-lg text-center mb-6 font-mono break-words"
            data-testid="global-error-detail"
          >
            {detail}
          </p>
        ) : (
          <div className="mb-6" />
        )}
        <button
          type="button"
          onClick={reset}
          className="rounded-sm border border-white/20 px-4 py-2 text-sm hover:bg-white/5"
        >
          Try again
        </button>
      </body>
    </html>
  );
}

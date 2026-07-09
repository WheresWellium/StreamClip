"use client";

import Link from "next/link";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/**
 * OpenAPI explorer embedded in Settings so users keep app chrome and a back path.
 * FastAPI serves /docs on the sidecar; this iframe stays inside the static shell.
 */
export function ApiDocsPanel() {
  return (
    <div className="space-y-4">
      <div>
        <Link href="/settings" className="text-sm text-sky-400 hover:underline">
          ← Back to Settings
        </Link>
        <h2 className="text-xl font-semibold mt-2">API reference</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Interactive OpenAPI docs for your local StreamClip sidecar. Same machine
          only — requests use your current session when you authorize in the explorer.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">OpenAPI (Swagger)</CardTitle>
          <CardDescription>
            Opens the sidecar&apos;s <code className="text-xs">/docs</code> endpoint below.
            Use <strong>Authorize</strong> with a Bearer token from Settings → Account after sign-in.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0 pt-0">
          <iframe
            src="/docs"
            title="StreamClip API documentation"
            className="w-full min-h-[min(70vh,720px)] border-0 border-t border-white/10 bg-background"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          />
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        Prefer raw JSON?{" "}
        <a href="/openapi.json" className="text-sky-400 hover:underline" target="_blank" rel="noreferrer">
          openapi.json
        </a>
      </p>
    </div>
  );
}

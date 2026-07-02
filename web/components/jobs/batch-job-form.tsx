"use client";

import { Layers } from "lucide-react";
import * as React from "react";

import { createBatchJobsAction } from "@/app/actions/jobs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/form";

export function BatchJobForm() {
  const [urls, setUrls] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);
  const [pending, setPending] = React.useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setMessage(null);
    const lines = urls
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    const result = await createBatchJobsAction(lines);
    setPending(false);
    setMessage(result.message);
    if (result.ok) setUrls("");
  }

  return (
    <Card className="border-white/10">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Layers className="h-4 w-4 text-sky-400" />
          Batch URLs
        </CardTitle>
        <CardDescription>
          Paste one URL per line (max 20). Each starts an independent job.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="batch_urls">URLs</Label>
            <textarea
              id="batch_urls"
              value={urls}
              onChange={(e) => setUrls(e.target.value)}
              rows={4}
              className="w-full rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-sky-400/60"
              placeholder="https://www.twitch.tv/videos/...&#10;https://youtube.com/watch?v=..."
            />
          </div>
          <Button type="submit" disabled={pending || !urls.trim()}>
            {pending ? "Queueing…" : "Queue batch"}
          </Button>
          {message && <p className="text-xs text-muted-foreground">{message}</p>}
        </form>
      </CardContent>
    </Card>
  );
}

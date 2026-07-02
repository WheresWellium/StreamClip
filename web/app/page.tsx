import { Suspense } from "react";

import { AuthPanel } from "@/components/auth/auth-panel";
import { BatchJobForm } from "@/components/jobs/batch-job-form";
import { CreateJobForm } from "@/components/jobs/create-job-form";
import { JobsList, JobsListSkeleton } from "@/components/jobs/jobs-list";
import { metaApi, templatesApi } from "@/lib/api/client";
import type { JobTemplate, StreamClipMeta } from "@/lib/api/meta-types";
import { getAccessToken } from "@/lib/auth/session";
import { normalizeStreamClipMeta } from "@/lib/normalize-meta";

function normalizeMeta(raw: Record<string, unknown>): StreamClipMeta {
  return normalizeStreamClipMeta(raw);
}

export default async function HomePage({
  searchParams,
}: {
  searchParams?: Promise<{ search?: string; status?: string }>;
}) {
  const token = await getAccessToken();
  const sp = (await searchParams) ?? {};
  const rawMeta = await metaApi.meta();
  const meta = normalizeMeta(rawMeta);

  let templates: JobTemplate[] = [];
  if (token) {
    try {
      templates = await templatesApi.list(token);
    } catch {
      templates = [];
    }
  }

  return (
    <div className="space-y-10 animate-fade-in">
      {/* Hero */}
      <section className="text-center sm:text-left space-y-3 pt-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-sky-400/30 bg-sky-400/10 text-xs text-sky-400 mb-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-400" />
          </span>
          AI clip pipeline
        </div>
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-foreground">
          Turn long-form video into{" "}
          <span className="text-sky-400">viral vertical shorts</span>
        </h1>
        <p className="text-muted-foreground max-w-xl text-base">
          Subject tracking, animated captions, and meme overlays — paste a URL or
          upload, then watch progress and download clips when ready.
        </p>
      </section>

      {/* Primary action — create job */}
      <div id="create">
        <CreateJobForm meta={meta} templates={templates} isAuthenticated={!!token} />
      </div>

      {!token && (
        <div className="rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-200/90">
          Jobs on this device are anonymous.{" "}
          <a href="/register" className="underline hover:text-amber-100">
            Create an account
          </a>{" "}
          to keep them across browsers and enable templates.
        </div>
      )}

      {/* Secondary flows */}
      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <Suspense fallback={<JobsListSkeleton />}>
          <JobsList searchParams={sp} />
        </Suspense>
        <aside className="space-y-4">
          <AuthPanel isAuthenticated={!!token} />
          <BatchJobForm />
        </aside>
      </div>
    </div>
  );
}

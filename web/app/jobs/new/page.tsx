"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CreateJobForm } from "@/components/jobs/create-job-form";
import { StackPreflightBanner } from "@/components/jobs/stack-preflight-banner";
import { metaApi, templatesApi } from "@/lib/api/client";
import type { JobTemplate, StreamClipMeta } from "@/lib/api/meta-types";
import { getClientAccessToken } from "@/lib/auth/client-session";
import { normalizeStreamClipMeta } from "@/lib/normalize-meta";

export default function NewJobPage() {
  const [meta, setMeta] = useState<StreamClipMeta | null>(null);
  const [templates, setTemplates] = useState<JobTemplate[]>([]);
  const [token, setToken] = useState<string | undefined>();

  useEffect(() => {
    let cancelled = false;
    const t = getClientAccessToken();
    setToken(t);
    void (async () => {
      const rawMeta = await metaApi.meta();
      const normalized = normalizeStreamClipMeta(rawMeta);
      let tpls: JobTemplate[] = [];
      if (t) {
        try {
          tpls = await templatesApi.list(t);
        } catch {
          tpls = [];
        }
      }
      if (!cancelled) {
        setMeta(normalized);
        setTemplates(tpls);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!meta) {
    return <p className="text-sm text-muted-foreground py-8">Loading…</p>;
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 animate-fade-in">
      <div className="space-y-1">
        <Link
          href="/jobs"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← All jobs
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight pt-2">New clip job</h1>
        <p className="text-sm text-muted-foreground">
          Paste a URL or upload a file — we find highlights, reframe to any ratio, and rank what wins.
        </p>
      </div>

      {!token && (
        <div className="rounded-sm border border-amber-400/40 bg-amber-400/10 px-4 py-2.5 text-sm text-amber-200/90">
          Jobs on this device are anonymous.{" "}
          <a href="/register" className="underline hover:text-amber-100">
            Create an account
          </a>{" "}
          to keep them across browsers and enable templates.
        </div>
      )}

      <StackPreflightBanner />

      <CreateJobForm meta={meta} templates={templates} isAuthenticated={!!token} />
    </div>
  );
}

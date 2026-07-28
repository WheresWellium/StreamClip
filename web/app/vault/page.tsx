"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { VaultClipsView } from "@/components/vault/vault-clips-view";
import { Button } from "@/components/ui/button";
import { vaultApi, type VaultQuotaResponse } from "@/lib/api/client";
import { getClientAccessToken } from "@/lib/auth/client-session";

function quotaBanner(warning: string | null, label: string) {
  if (!warning) return null;
  const tone =
    warning === "exceeded" || warning === "critical"
      ? "text-rose-400/90 border-rose-500/30 bg-rose-500/10"
      : "text-amber-400/90 border-amber-500/30 bg-amber-500/10";
  const message =
    warning === "exceeded"
      ? `${label} quota exceeded — remove clips to save more.`
      : warning === "critical"
        ? `${label} quota almost full — free up space soon.`
        : `${label} quota approaching — consider removing old clips.`;
  return (
    <p className={`text-sm rounded-lg border px-4 py-3 ${tone}`}>{message}</p>
  );
}

export default function VaultPage() {
  const router = useRouter();
  const [clips, setClips] = useState<Awaited<ReturnType<typeof vaultApi.list>>>([]);
  const [quota, setQuota] = useState<VaultQuotaResponse | null>(null);
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    const token = getClientAccessToken();
    if (!token) {
      router.replace("/login?next=/vault");
      return;
    }
    let cancelled = false;
    void Promise.all([vaultApi.list(token), vaultApi.quota(token)])
      .then(([list, q]) => {
        if (!cancelled) {
          setClips(list);
          setQuota(q);
          setLoadError(null);
          setReady(true);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(
            err instanceof Error ? err.message : "Could not load vault. Try again.",
          );
          setReady(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (!ready) {
    return <p className="text-sm text-muted-foreground text-center py-12">Loading vault…</p>;
  }

  if (loadError) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-8 space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight">Clip Vault</h1>
        <p role="alert" className="text-sm text-destructive rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3">
          {loadError}
        </p>
        <Button type="button" variant="outline" onClick={() => window.location.reload()}>
          Retry
        </Button>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Clip Vault</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Saved clips ready to publish or schedule. Distinct from sticker assets in Settings.
          </p>
        </div>
        {quota ? (
          <div className="text-sm font-mono text-muted-foreground space-y-0.5 text-right">
            <p>
              {quota.clips.used} / {quota.clips.limit} clips
            </p>
            <p>
              {quota.bytes.used_human} / {quota.bytes.limit_human}
            </p>
          </div>
        ) : null}
      </div>

      {quota ? quotaBanner(quota.clips.warning, "Clip") : null}
      {quota ? quotaBanner(quota.bytes.warning, "Storage") : null}

      {clips.length === 0 ? (
        <div className="glossy-surface rounded-lg border border-border/60 p-12 text-center space-y-4">
          <p className="text-muted-foreground">No saved clips yet.</p>
          <Link
            href="/jobs"
            className="inline-flex items-center justify-center rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500"
          >
            Go to Jobs
          </Link>
        </div>
      ) : (
        <VaultClipsView clips={clips} />
      )}
    </main>
  );
}

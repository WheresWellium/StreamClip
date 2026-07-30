"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { HealthChecklist, type StackHealthSnapshot } from "@/components/onboarding/health-checklist";
import { metaApi } from "@/lib/api/client";
import { devToolsEnabled } from "@/lib/dev-tools";
import { helpHref } from "@/lib/docs";

export function StackPreflightBanner() {
  const [data, setData] = useState<StackHealthSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const stack = await metaApi.stackHealth();
      setData(stack);
    } catch {
      setData({ status: "error", checks: {}, worker: false });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const coreDown =
    !loading &&
    data != null &&
    (data.status !== "ok" ||
      !data.checks.database ||
      !data.checks.storage ||
      (data.checks.redis === false));

  if (!coreDown) return null;

  return (
    <div className="rounded-sm border border-amber-400/40 bg-amber-400/10 px-4 py-3 space-y-3">
      <p className="text-sm text-amber-100/95 font-medium">
        Needs attention — jobs may fail until services recover.
      </p>
      <HealthChecklist data={data} loading={loading} onRetry={() => void load()} />
      <p className="text-xs text-muted-foreground">
        <Link href="/onboarding" className="underline hover:text-foreground">
          Run setup wizard
        </Link>
        {" · "}
        <Link href={helpHref("/")} className="underline hover:text-foreground">
          Help
        </Link>
        {devToolsEnabled ? (
          <>
            {" "}
            · Docker beta:{" "}
            <code className="text-[11px]">.\scripts\start_local.ps1</code>
          </>
        ) : null}
      </p>
    </div>
  );
}

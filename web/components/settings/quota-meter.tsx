"use client";

import Link from "next/link";
import { useState } from "react";

import { Progress } from "@/components/ui/form";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { VaultQuotaResponse } from "@/lib/api/client";
import { dismissQuotaTooltip, hasDismissedQuotaTooltip } from "@/lib/settings-storage";
import { cn } from "@/lib/utils/format";

type QuotaWarning = "approaching" | "critical" | "exceeded" | null;

function pct(used: number, limit: number): number {
  if (limit <= 0) return 0;
  return Math.min(100, Math.round((used / limit) * 100));
}

function clipsLabel(warning: QuotaWarning, used: number, limit: number): string {
  switch (warning) {
    case "approaching":
      return "Running low on vault clips";
    case "critical":
      return "Vault nearly full";
    case "exceeded":
      return "Vault full — delete clips or upgrade";
    default:
      return `${used} of ${limit} clips saved`;
  }
}

function bytesLabel(warning: QuotaWarning, usedHuman: string, limitHuman: string): string {
  switch (warning) {
    case "approaching":
      return "Storage almost full — archive or upgrade";
    case "critical":
      return "Less than 1 GB left";
    case "exceeded":
      return "Storage full — delete clips or upgrade";
    default:
      return `${usedHuman} of ${limitHuman}`;
  }
}

function barTone(warning: QuotaWarning): string {
  if (warning === "exceeded" || warning === "critical") {
    return "[&>div]:bg-rose-500";
  }
  if (warning === "approaching") {
    return "[&>div]:bg-amber-500";
  }
  return "[&>div]:bg-sky-500";
}

type Props = {
  quota: VaultQuotaResponse;
  className?: string;
};

export function QuotaMeter({ quota, className }: Props) {
  const clipsWarning = quota.clips.warning as QuotaWarning;
  const bytesWarning = quota.bytes.warning as QuotaWarning;
  const anyWarning = clipsWarning ?? bytesWarning;
  const [dismissed, setDismissed] = useState(hasDismissedQuotaTooltip);

  function handleDismiss() {
    dismissQuotaTooltip();
    setDismissed(true);
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Vault storage</CardTitle>
        <CardDescription>
          {quota.tier.toUpperCase()} plan — clips and storage on this account.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <div className="flex justify-between text-sm">
            <span
              className={cn(
                clipsWarning && clipsWarning !== "approaching"
                  ? "text-rose-400"
                  : clipsWarning
                    ? "text-amber-400"
                    : "text-muted-foreground",
              )}
            >
              {clipsLabel(clipsWarning, quota.clips.used, quota.clips.limit)}
            </span>
            <span className="text-xs text-muted-foreground font-mono">
              {pct(quota.clips.used, quota.clips.limit)}%
            </span>
          </div>
          <Progress
            value={pct(quota.clips.used, quota.clips.limit)}
            className={barTone(clipsWarning)}
          />
        </div>

        <div className="space-y-1.5">
          <div className="flex justify-between text-sm">
            <span
              className={cn(
                bytesWarning && bytesWarning !== "approaching"
                  ? "text-rose-400"
                  : bytesWarning
                    ? "text-amber-400"
                    : "text-muted-foreground",
              )}
            >
              {bytesLabel(bytesWarning, quota.bytes.used_human, quota.bytes.limit_human)}
            </span>
            <span className="text-xs text-muted-foreground font-mono">
              {pct(quota.bytes.used, quota.bytes.limit)}%
            </span>
          </div>
          <Progress
            value={pct(quota.bytes.used, quota.bytes.limit)}
            className={barTone(bytesWarning)}
          />
        </div>

        {anyWarning ? (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <Link href="/settings?section=billing" className="text-sky-400 hover:underline">
              View plans and upgrade →
            </Link>
            {!dismissed ? (
              <Button type="button" variant="ghost" size="sm" onClick={handleDismiss}>
                Got it
              </Button>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

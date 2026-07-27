"use client";

import Link from "next/link";
import { CheckCircle2, Circle } from "lucide-react";
import { useEffect, useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { distributionApi, jobsApi, vaultApi } from "@/lib/api/client";
import {
  DeviceProfileCard,
  StorageStatusCard,
} from "@/components/onboarding/device-storage-cards";
import {
  getClientAccessToken,
  getClientDeviceId,
} from "@/lib/auth/client-session";
import { hasDistributionAccess } from "@/lib/distribution/client-access";
import { getLicenseMachineId } from "@/lib/license-machine-id";
import {
  hasDismissedQuotaTooltip,
  hasSeenVault,
} from "@/lib/settings-storage";

type CheckItem = {
  id: string;
  label: string;
  done: boolean;
  hint?: string;
  href?: string;
};

async function fetchLicenseActive(machineId: string): Promise<boolean> {
  try {
    const res = await fetch(
      `/api/license/status?machine_id=${encodeURIComponent(machineId)}`,
      { cache: "no-store" },
    );
    if (!res.ok) return false;
    const data = (await res.json()) as { active?: boolean; tier?: string };
    return Boolean(data.active && data.tier && data.tier !== "free");
  } catch {
    return false;
  }
}

export function ActivationChecklist() {
  const [items, setItems] = useState<CheckItem[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const token = getClientAccessToken();
      const deviceId = getClientDeviceId();
      const signedIn = Boolean(token);
      const licenseActive = await fetchLicenseActive(getLicenseMachineId());
      const hasPro = token ? await hasDistributionAccess(token) : licenseActive;

      let oauthConfigured = false;
      let platformConnected = false;
      if (token && hasPro) {
        try {
          const apps = await distributionApi.oauthApps(token);
          oauthConfigured = apps.some((a) => a.configured);
        } catch {
          oauthConfigured = false;
        }
        try {
          const connections = await distributionApi.connections(token);
          platformConnected = connections.length > 0;
        } catch {
          platformConnected = false;
        }
      }

      let firstJobDone = false;
      try {
        const jobs = await jobsApi.list(10, 0, token ?? undefined, { status: "done" }, deviceId);
        firstJobDone = jobs.jobs.length > 0;
      } catch {
        firstJobDone = false;
      }

      let quotaHealthy = true;
      if (token) {
        try {
          const quota = await vaultApi.quota(token);
          const hasWarning = Boolean(quota.clips.warning ?? quota.bytes.warning);
          quotaHealthy = !hasWarning || hasDismissedQuotaTooltip();
        } catch {
          quotaHealthy = hasDismissedQuotaTooltip();
        }
      }

      const next: CheckItem[] = [
        {
          id: "account",
          label: "Account created or signed in",
          done: signedIn,
          hint: signedIn ? undefined : "Register or sign in to sync jobs.",
          href: signedIn ? undefined : "/register",
        },
        {
          id: "license",
          label: "License activated",
          done: licenseActive,
          hint: licenseActive ? undefined : "Paste your Pro key in License.",
          href: "/settings?section=license",
        },
        {
          id: "oauth",
          label: "OAuth apps configured (Pro)",
          done: !hasPro || oauthConfigured,
          hint: hasPro && !oauthConfigured ? "Add YouTube/TikTok app credentials." : undefined,
          href: "/settings?section=integrations",
        },
        {
          id: "connected",
          label: "Platform connected",
          done: platformConnected,
          hint: platformConnected ? undefined : "Connect YouTube or TikTok.",
          href: "/settings?section=distribution",
        },
        {
          id: "first-job",
          label: "First job completed",
          done: firstJobDone,
          hint: firstJobDone ? undefined : "Run a clip job from a VOD or upload.",
          href: "/jobs/new",
        },
        {
          id: "vault-review",
          label: "Review vault storage",
          done: hasSeenVault(),
          hint: hasSeenVault() ? undefined : "See how many clips and GB your plan includes.",
          href: "/settings?section=vault",
        },
        {
          id: "quota-understood",
          label: "Understand storage limits",
          done: quotaHealthy,
          hint: quotaHealthy
            ? undefined
            : "Free: 25 clips and 10 GB. Upgrade for more.",
          href: "/settings?section=billing",
        },
      ];
      if (!cancelled) setItems(next);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!items) {
    return <p className="text-sm text-muted-foreground py-4">Loading checklist…</p>;
  }

  const doneCount = items.filter((i) => i.done).length;

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Set up qClip</h2>
        <p className="text-sm text-muted-foreground">
          Confirm this device and where clips are saved, then finish activation.
        </p>
        <DeviceProfileCard />
        <StorageStatusCard />
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Activation checklist</CardTitle>
          <CardDescription>
            {doneCount} of {items.length} complete — finish setup to publish clips.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {items.map((item) => (
            <div key={item.id} className="flex items-start gap-3 text-sm">
              {item.done ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <Circle className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
              )}
              <div className="min-w-0">
                {item.href && !item.done ? (
                  <Link href={item.href} className="text-sky-400 hover:underline">
                    {item.label}
                  </Link>
                ) : (
                  <span className={item.done ? "text-foreground" : "text-muted-foreground"}>
                    {item.label}
                  </span>
                )}
                {item.hint ? (
                  <p className="text-xs text-muted-foreground mt-0.5">{item.hint}</p>
                ) : null}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

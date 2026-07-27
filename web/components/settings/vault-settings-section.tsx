"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { QuotaMeter } from "@/components/settings/quota-meter";
import { VaultClipsView } from "@/components/vault/vault-clips-view";
import {
  DeviceProfileCard,
  StorageStatusCard,
} from "@/components/onboarding/device-storage-cards";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { vaultApi, type VaultClip, type VaultQuotaResponse } from "@/lib/api/client";
import { getClientAccessToken } from "@/lib/auth/client-session";
import { markVaultSeen } from "@/lib/settings-storage";

export function VaultSettingsSection() {
  const [clips, setClips] = useState<VaultClip[]>([]);
  const [quota, setQuota] = useState<VaultQuotaResponse | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    markVaultSeen();
    const token = getClientAccessToken();
    if (!token) {
      setReady(true);
      return;
    }
    let cancelled = false;
    void Promise.all([vaultApi.list(token), vaultApi.quota(token)])
      .then(([list, q]) => {
        if (!cancelled) {
          setClips(list);
          setQuota(q);
          setReady(true);
        }
      })
      .catch(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) {
    return <p className="text-sm text-muted-foreground py-4">Loading vault…</p>;
  }

  const token = getClientAccessToken();
  if (!token) {
    return (
      <div className="space-y-6">
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Saved on this device</h2>
          <StorageStatusCard />
          <DeviceProfileCard />
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Clip vault</CardTitle>
            <CardDescription>Sign in to view saved clips and plan quotas.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/login?next=/settings?section=vault" className="text-sky-400 hover:underline text-sm">
              Sign in →
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Saved on this device</h2>
        <StorageStatusCard />
      </div>
      {quota ? <QuotaMeter quota={quota} /> : null}

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>Saved clips</CardTitle>
            <CardDescription>
              Clips saved from jobs for publishing or scheduling.
            </CardDescription>
          </div>
          <Link href="/vault" className="text-sm text-sky-400 hover:underline shrink-0">
            Open full vault →
          </Link>
        </CardHeader>
        <CardContent>
          {clips.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No saved clips yet. Save a clip from a completed job to fill your vault.
            </p>
          ) : (
            <VaultClipsView clips={clips} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DistributionConnections } from "@/components/distribution/distribution-connections";
import { DistributionOAuthToasts } from "@/components/distribution/distribution-oauth-toasts";
import { DistributionQueue } from "@/components/distribution/distribution-queue";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { distributionApi } from "@/lib/api/client";
import { getClientAccessToken } from "@/lib/auth/client-session";
import { hasDistributionAccess } from "@/lib/distribution/client-access";

type Props = {
  oauthConnected?: string;
  oauthError?: string;
};

export function DistributionSection({ oauthConnected, oauthError }: Props) {
  const [token, setToken] = useState<string | undefined>();
  const [hasPro, setHasPro] = useState(false);
  const [platforms, setPlatforms] = useState<Awaited<ReturnType<typeof distributionApi.platforms>>>([]);
  const [connections, setConnections] = useState<Awaited<ReturnType<typeof distributionApi.connections>>>([]);
  const [publishJobs, setPublishJobs] = useState<Awaited<ReturnType<typeof distributionApi.publishJobs>>>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const t = getClientAccessToken();
    setToken(t);
    if (!t) {
      setReady(true);
      return;
    }
    void (async () => {
      const pro = await hasDistributionAccess(t);
      let plats: typeof platforms = [];
      let conns: typeof connections = [];
      let jobs: typeof publishJobs = [];
      try {
        [plats, conns, jobs] = await Promise.all([
          distributionApi.platforms(t),
          distributionApi.connections(t),
          distributionApi.publishJobs(t),
        ]);
      } catch {
        plats = [];
        conns = [];
        jobs = [];
      }
      if (!cancelled) {
        setHasPro(pro);
        setPlatforms(plats);
        setConnections(conns);
        setPublishJobs(jobs);
        setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) {
    return <p className="text-sm text-muted-foreground py-4">Loading distribution…</p>;
  }

  if (!token) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Distribution</CardTitle>
          <CardDescription>Sign in to connect platforms and publish clips.</CardDescription>
        </CardHeader>
        <CardContent>
          <Link href="/login?next=/settings%3Fsection%3Ddistribution" className="text-sky-400 hover:underline text-sm">
            Sign in →
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <DistributionOAuthToasts connected={oauthConnected} error={oauthError} />

      {!hasPro && (
        <p className="text-sm text-amber-400/90 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3">
          Publishing and platform connections require Pro.{" "}
          <Link href="/settings?section=license" className="underline hover:text-amber-300">
            Activate a license
          </Link>{" "}
          to connect accounts.
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Connections</CardTitle>
          <CardDescription>
            Link your creator accounts. Configure OAuth apps under Integrations first.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DistributionConnections
            platforms={platforms}
            connections={connections}
            hasPro={hasPro}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Publish queue</CardTitle>
          <CardDescription>Scheduled and in-progress publishes.</CardDescription>
        </CardHeader>
        <CardContent>
          <DistributionQueue jobs={publishJobs} hasPro={hasPro} />
        </CardContent>
      </Card>
    </div>
  );
}

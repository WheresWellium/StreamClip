"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

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
import {
  DISTRIBUTION_LOGIN_NEXT,
} from "@/lib/distribution/routes";

type Props = {
  oauthConnected?: string;
  oauthError?: string;
};

export function DistributionSection({ oauthConnected, oauthError }: Props) {
  const [token, setToken] = useState<string | undefined>();
  const [hasPro, setHasPro] = useState(false);
  const [platforms, setPlatforms] = useState<
    Awaited<ReturnType<typeof distributionApi.platforms>>
  >([]);
  const [connections, setConnections] = useState<
    Awaited<ReturnType<typeof distributionApi.connections>>
  >([]);
  const [publishJobs, setPublishJobs] = useState<
    Awaited<ReturnType<typeof distributionApi.publishJobs>>
  >([]);
  const [ready, setReady] = useState(false);

  const refetch = useCallback(async () => {
    const t = getClientAccessToken();
    setToken(t);
    const pro = await hasDistributionAccess(t);
    let plats: typeof platforms = [];
    let conns: typeof connections = [];
    let jobs: typeof publishJobs = [];
    if (t) {
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
    }
    setHasPro(pro);
    setPlatforms(plats);
    setConnections(conns);
    setPublishJobs(jobs);
    setReady(true);
  }, []);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  if (!ready) {
    return <p className="text-sm text-muted-foreground py-4">Loading distribution…</p>;
  }

  if (!token && !hasPro) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Distribution</CardTitle>
          <CardDescription>Sign in to connect platforms and publish clips.</CardDescription>
        </CardHeader>
        <CardContent>
          <Link href={DISTRIBUTION_LOGIN_NEXT} className="text-sky-400 hover:underline text-sm">
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
            Link your creator accounts. Configure OAuth apps under{" "}
            <Link href="/settings?section=integrations" className="text-sky-400 hover:underline">
              Integrations
            </Link>{" "}
            first.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DistributionConnections
            platforms={platforms}
            connections={connections}
            hasPro={hasPro}
            onRefresh={refetch}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Publish queue</CardTitle>
          <CardDescription>Scheduled and in-progress publishes.</CardDescription>
        </CardHeader>
        <CardContent>
          <DistributionQueue jobs={publishJobs} hasPro={hasPro} onRefresh={refetch} />
        </CardContent>
      </Card>
    </div>
  );
}

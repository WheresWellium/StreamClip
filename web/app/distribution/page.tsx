import Link from "next/link";
import { redirect } from "next/navigation";

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
import { getAccessToken } from "@/lib/auth/session";
import { hasDistributionAccess } from "@/lib/distribution/access";

export default async function DistributionPage({
  searchParams,
}: {
  searchParams?: Promise<{ connected?: string; error?: string }>;
}) {
  const sp = (await searchParams) ?? {};
  const token = await getAccessToken();
  if (!token) {
    redirect("/login?next=/distribution");
  }

  const hasPro = await hasDistributionAccess(token);

  let platforms: Awaited<ReturnType<typeof distributionApi.platforms>> = [];
  let connections: Awaited<ReturnType<typeof distributionApi.connections>> = [];
  let publishJobs: Awaited<ReturnType<typeof distributionApi.publishJobs>> = [];
  try {
    [platforms, connections, publishJobs] = await Promise.all([
      distributionApi.platforms(token),
      distributionApi.connections(token),
      distributionApi.publishJobs(token),
    ]);
  } catch {
    platforms = [];
    connections = [];
    publishJobs = [];
  }

  return (
    <main className="mx-auto max-w-2xl space-y-6">
      <DistributionOAuthToasts connected={sp.connected} error={sp.error} />

      <div>
        <Link href="/settings" className="text-sm text-sky-400 hover:underline">
          ← Settings
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight mt-2">Distribution</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Connect YouTube Shorts and TikTok, then publish or schedule clips from your Vault.
        </p>
      </div>

      {!hasPro && (
        <p className="text-sm text-amber-400/90 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3">
          Publishing and platform connections require Pro.{" "}
          <Link href="/settings" className="underline hover:text-amber-300">
            Activate a license in Settings
          </Link>{" "}
          to connect accounts.
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Connections</CardTitle>
          <CardDescription>
            Link your creator accounts. Configure OAuth apps in{" "}
            <Link href="/settings" className="text-sky-400 hover:underline">
              Settings
            </Link>{" "}
            before connecting.
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
          <CardDescription>
            Scheduled and in-progress publishes, plus recent activity.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DistributionQueue jobs={publishJobs} hasPro={hasPro} />
        </CardContent>
      </Card>
    </main>
  );
}

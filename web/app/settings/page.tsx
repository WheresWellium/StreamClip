import Link from "next/link";

import { AuthPanel } from "@/components/auth/auth-panel";
import { LicensePanel } from "@/components/settings/license-panel";
import { OAuthSetupWizard } from "@/components/settings/oauth-setup-wizard";
import { distributionApi, type OAuthAppConfig } from "@/lib/api/client";
import { hasDistributionAccess } from "@/lib/distribution/access";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getAccessToken } from "@/lib/auth/session";

const DEFAULT_OAUTH_APPS: OAuthAppConfig[] = [
  {
    platform: "youtube_shorts",
    client_id: "",
    redirect_uri: "/api/distribution/oauth/youtube_shorts/callback",
    configured: false,
  },
  {
    platform: "tiktok",
    client_id: "",
    redirect_uri: "/api/distribution/oauth/tiktok/callback",
    configured: false,
  },
];

export default async function SettingsPage() {
  const token = await getAccessToken();
  const hasPro = token ? await hasDistributionAccess(token) : false;

  let oauthApps = DEFAULT_OAUTH_APPS;
  if (token && hasPro) {
    try {
      oauthApps = await distributionApi.oauthApps(token);
    } catch {
      oauthApps = DEFAULT_OAUTH_APPS;
    }
  }

  return (
    <div className="space-y-8 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Profile, integrations, retention, and license.
        </p>
      </div>

      <AuthPanel isAuthenticated={!!token} />

      <Card>
        <CardHeader>
          <CardTitle>Webhooks</CardTitle>
          <CardDescription>
            Per-user webhook URL for job.completed events (requires sign-in).
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Configure via API <code className="text-xs">PATCH /api/settings/webhooks</code> or
          use the OpenAPI docs.
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Retention</CardTitle>
          <CardDescription>
            Terminal jobs older than the retention window are purged automatically.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Default: 7 days. Adjust <code className="text-xs">job_retention.retention_days</code> in
          config.yaml.
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Storage & worker</CardTitle>
          <CardDescription>Local MinIO or S3-compatible backend.</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Celery workers process the GPU queue. Enable the <code className="text-xs">gpu</code>{" "}
          compose profile for NVIDIA transcoding.
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Device</CardTitle>
          <CardDescription>
            Anonymous jobs are scoped to your browser device cookie.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Sign in and use &quot;Link jobs&quot; after login to attach device jobs to your account.
        </CardContent>
      </Card>

      <LicensePanel />

      {token ? (
        <OAuthSetupWizard apps={oauthApps} hasPro={hasPro} />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Platform OAuth apps</CardTitle>
            <CardDescription>
              Sign in to configure YouTube and TikTok OAuth credentials.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      <p className="text-sm">
        <Link href="/settings/templates" className="text-sky-400 hover:underline">
          Manage job templates →
        </Link>
        {" · "}
        <Link href="/distribution" className="text-sky-400 hover:underline">
          Distribution →
        </Link>
      </p>
    </div>
  );
}

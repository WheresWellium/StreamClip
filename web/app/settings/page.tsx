"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { AuthPanel } from "@/components/auth/auth-panel";
import { ActivationChecklist } from "@/components/settings/activation-checklist";
import { DistributionSection } from "@/components/settings/distribution-section";
import { LicensePanel } from "@/components/settings/license-panel";
import { OAuthSetupWizard } from "@/components/settings/oauth-setup-wizard";
import { PrivacyPanel } from "@/components/settings/privacy-panel";
import { WebhookPanel } from "@/components/settings/webhook-panel";
import {
  distributionApi,
  settingsApi,
  type OAuthAppConfig,
} from "@/lib/api/client";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getClientAccessToken } from "@/lib/auth/client-session";
import { hasDistributionAccess } from "@/lib/distribution/client-access";

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

type SettingsSection =
  | "account"
  | "get-started"
  | "license"
  | "distribution"
  | "integrations"
  | "privacy"
  | "advanced";

export default function SettingsPage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground py-8">Loading settings…</p>}>
      <SettingsPageContent />
    </Suspense>
  );
}

function SettingsPageContent() {
  const searchParams = useSearchParams();
  const section = (searchParams.get("section") as SettingsSection | null) ?? "account";
  const oauthConnected = searchParams.get("connected") ?? undefined;
  const oauthError = searchParams.get("error") ?? undefined;

  const [token, setToken] = useState<string | undefined>();
  const [hasPro, setHasPro] = useState(false);
  const [oauthApps, setOauthApps] = useState(DEFAULT_OAUTH_APPS);
  const [privacyOptIn, setPrivacyOptIn] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const t = getClientAccessToken();
    setToken(t);
    void (async () => {
      let pro = false;
      let apps = DEFAULT_OAUTH_APPS;
      let optIn = false;
      if (t) {
        pro = await hasDistributionAccess(t);
        if (pro) {
          try {
            apps = await distributionApi.oauthApps(t);
          } catch {
            apps = DEFAULT_OAUTH_APPS;
          }
        }
        if (section === "privacy") {
          try {
            const privacy = await settingsApi.getPrivacy(t);
            optIn = privacy.data_contribution_opt_in;
          } catch {
            optIn = false;
          }
        }
      }
      if (!cancelled) {
        setHasPro(pro);
        setOauthApps(apps);
        setPrivacyOptIn(optIn);
        setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [section]);

  if (!ready && (section === "integrations" || section === "privacy")) {
    return <p className="text-sm text-muted-foreground py-8">Loading settings…</p>;
  }

  if (section === "get-started") {
    return <ActivationChecklist />;
  }

  if (section === "license") {
    return <LicensePanel />;
  }

  if (section === "distribution") {
    return (
      <DistributionSection oauthConnected={oauthConnected} oauthError={oauthError} />
    );
  }

  if (section === "integrations") {
    return (
      <div className="space-y-6">
        <WebhookPanel isAuthenticated={!!token} />
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
      </div>
    );
  }

  if (section === "privacy") {
    return <PrivacyPanel isAuthenticated={!!token} initialOptIn={privacyOptIn} />;
  }

  if (section === "advanced") {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Retention</CardTitle>
            <CardDescription>
              Terminal jobs older than the retention window are purged automatically.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Default: 7 days. Adjust{" "}
            <code className="text-xs">job_retention.retention_days</code> in config.yaml.
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Storage & worker</CardTitle>
            <CardDescription>Local storage backend on desktop installs.</CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            The embedded sidecar runs an in-process worker for clip jobs.
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Device</CardTitle>
            <CardDescription>
              Anonymous jobs are scoped to your browser device id.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Sign in and use &quot;Link jobs&quot; after login to attach device jobs to your
            account.
          </CardContent>
        </Card>

        <p className="text-sm">
          <Link href="/settings/templates" className="text-sky-400 hover:underline">
            Manage job templates →
          </Link>
          {" · "}
          <Link href="/settings/assets" className="text-sky-400 hover:underline">
            Overlay assets →
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <AuthPanel isAuthenticated={!!token} />
      <p className="text-sm text-muted-foreground">
        New here?{" "}
        <Link href="/settings?section=get-started" className="text-sky-400 hover:underline">
          Open the activation checklist →
        </Link>
      </p>
    </div>
  );
}

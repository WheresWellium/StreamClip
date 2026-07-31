"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { AdminLicensePanel } from "@/components/settings/admin-license-panel";
import { AuthPanel } from "@/components/auth/auth-panel";
import { OPEN_CLAIM_EVENT } from "@/components/auth/auth-extras";
import { ActivationChecklist } from "@/components/settings/activation-checklist";
import { BillingPanel } from "@/components/settings/billing-panel";
import { CreatorToolsCard } from "@/components/settings/creator-tools-card";
import { DistributionSection } from "@/components/settings/distribution-section";
import { LicensePanel } from "@/components/settings/license-panel";
import { OAuthSetupWizard } from "@/components/settings/oauth-setup-wizard";
import { PrivacyPanel } from "@/components/settings/privacy-panel";
import { QuotaMeter } from "@/components/settings/quota-meter";
import { VaultSettingsSection } from "@/components/settings/vault-settings-section";
import { WebhookPanel } from "@/components/settings/webhook-panel";
import { Button } from "@/components/ui/button";
import { devToolsEnabled } from "@/lib/dev-tools";
import {
  isDeveloperIntegrationsEnabled,
  setDeveloperIntegrationsEnabled,
} from "@/lib/developer-integrations";
import {
  authApi,
  distributionApi,
  settingsApi,
  vaultApi,
  type OAuthAppConfig,
  type UserPreferences,
  type VaultQuotaResponse,
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
import type { SettingsSection } from "@/components/settings/settings-nav";

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
  const [isAdmin, setIsAdmin] = useState(false);
  const [oauthApps, setOauthApps] = useState(DEFAULT_OAUTH_APPS);
  const [privacyOptIn, setPrivacyOptIn] = useState(false);
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [vaultQuota, setVaultQuota] = useState<VaultQuotaResponse | null>(null);
  const [developerIntegrations, setDeveloperIntegrations] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setDeveloperIntegrations(isDeveloperIntegrationsEnabled());
  }, []);

  useEffect(() => {
    let cancelled = false;
    const t = getClientAccessToken();
    setToken(t);
    void (async () => {
      let pro = false;
      let admin = false;
      let apps = DEFAULT_OAUTH_APPS;
      let optIn = false;
      let prefs: UserPreferences | null = null;
      let quota: VaultQuotaResponse | null = null;
      if (t) {
        pro = await hasDistributionAccess(t);
        try {
          const me = await authApi.me(t);
          admin = me.tier === "admin";
        } catch {
          admin = false;
        }
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
          try {
            prefs = await settingsApi.getPreferences(t);
          } catch {
            prefs = null;
          }
        }
        if (section === "account") {
          try {
            quota = await vaultApi.quota(t);
          } catch {
            quota = null;
          }
        }
      }
      if (!cancelled) {
        setHasPro(pro);
        setIsAdmin(admin);
        setOauthApps(apps);
        setPrivacyOptIn(optIn);
        setPreferences(prefs);
        setVaultQuota(quota);
        setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [section]);

  if (!ready && (section === "integrations" || section === "privacy" || section === "account")) {
    return <p className="text-sm text-muted-foreground py-8">Loading settings…</p>;
  }

  if (section === "get-started") {
    return <ActivationChecklist />;
  }

  if (section === "license") {
    return <LicensePanel />;
  }

  if (section === "vault") {
    return <VaultSettingsSection />;
  }

  if (section === "billing") {
    return <BillingPanel />;
  }

  if (section === "distribution") {
    return (
      <DistributionSection oauthConnected={oauthConnected} oauthError={oauthError} />
    );
  }

  if (section === "integrations") {
    const showWebhooks = devToolsEnabled || developerIntegrations;

    return (
      <div className="space-y-6">
        {!devToolsEnabled && hasPro && (
          <Card>
            <CardHeader>
              <CardTitle>Developer integrations</CardTitle>
              <CardDescription>
                Webhooks and custom automation for power users.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  const next = !developerIntegrations;
                  setDeveloperIntegrationsEnabled(next);
                  setDeveloperIntegrations(next);
                }}
              >
                {developerIntegrations ? "Hide webhook settings" : "Show webhook settings"}
              </Button>
            </CardContent>
          </Card>
        )}
        {showWebhooks && <WebhookPanel isAuthenticated={!!token} />}
        {token ? (
          <OAuthSetupWizard apps={oauthApps} hasPro={hasPro} />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Publish setup</CardTitle>
              <CardDescription>
                Sign in to configure YouTube and TikTok publish credentials.
              </CardDescription>
            </CardHeader>
          </Card>
        )}
      </div>
    );
  }

  if (section === "privacy") {
    return (
      <PrivacyPanel
        isAuthenticated={!!token}
        initialOptIn={privacyOptIn}
        initialPreferences={preferences}
      />
    );
  }

  if (section === "advanced") {
    if (!devToolsEnabled) {
      return <CreatorToolsCard />;
    }

    return (
      <div className="space-y-6">
        {isAdmin && token && (
          <Card>
            <CardHeader>
              <CardTitle>Admin — license revoke</CardTitle>
              <CardDescription>Operator tools (admin tier only).</CardDescription>
            </CardHeader>
            <CardContent>
              <AdminLicensePanel />
            </CardContent>
          </Card>
        )}

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

        <CreatorToolsCard />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {token && vaultQuota ? <QuotaMeter quota={vaultQuota} /> : null}
      <AuthPanel isAuthenticated={!!token} />
      {token ? (
        <Card>
          <CardHeader>
            <CardTitle>Local jobs</CardTitle>
            <CardDescription>
              Attach anonymous jobs created on this device to your account.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              variant="outline"
              onClick={() => window.dispatchEvent(new Event(OPEN_CLAIM_EVENT))}
            >
              Link local jobs
            </Button>
          </CardContent>
        </Card>
      ) : null}
      <CreatorToolsCard />
      <p className="text-sm text-muted-foreground">
        New here?{" "}
        <Link href="/settings?section=get-started" className="text-sky-400 hover:underline">
          Open the activation checklist →
        </Link>
      </p>
    </div>
  );
}

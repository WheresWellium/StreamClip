"use client";

import Link from "next/link";
import { useActionState, useEffect } from "react";

import {
  updateOAuthAppAction,
  type DistributionActionState,
} from "@/lib/api/actions/distribution";
import { useToastSafe } from "@/components/providers/toast-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { OAuthAppConfig } from "@/lib/api/client";
import { DISTRIBUTION_SETTINGS_HREF } from "@/lib/distribution/routes";
import { helpHref } from "@/lib/docs";

const PLATFORM_LABELS: Record<string, string> = {
  youtube_shorts: "YouTube Shorts",
  tiktok: "TikTok",
};

/** Desktop Electron sidecar origin — see docs/tutorials/TUTORIAL_PUBLISH_YOUTUBE.md */
const DESKTOP_REDIRECT_URIS: Record<string, string> = {
  youtube_shorts:
    "http://127.0.0.1:8765/api/distribution/oauth/youtube_shorts/callback",
  tiktok: "http://127.0.0.1:8765/api/distribution/oauth/tiktok/callback",
};

const GOOGLE_CREDENTIALS_URL =
  "https://console.cloud.google.com/apis/credentials";
const TIKTOK_LOGIN_KIT_URL =
  "https://developers.tiktok.com/doc/login-kit-web/";

const initial: DistributionActionState = { status: "idle" };

type Props = {
  apps: OAuthAppConfig[];
  hasPro: boolean;
};

function CopyUriButton({ uri, label }: { uri: string; label: string }) {
  const { push: toast } = useToastSafe();
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className="h-7 shrink-0 px-2 text-[11px]"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(uri);
          toast("Copied", `${label} copied to clipboard.`);
        } catch {
          toast("Copy failed", "Select the URI and copy it manually.");
        }
      }}
    >
      Copy
    </Button>
  );
}

function RedirectUriRow({
  label,
  uri,
  hint,
}: {
  label: string;
  uri: string;
  hint: string;
}) {
  return (
    <div className="space-y-1 rounded-md border border-border/50 bg-muted/20 px-2.5 py-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-0.5">
          <p className="text-[11px] font-medium text-foreground/90">{label}</p>
          <code className="block break-all text-[11px] text-foreground/90">
            {uri}
          </code>
        </div>
        <CopyUriButton uri={uri} label={label} />
      </div>
      <p className="text-[10px] text-muted-foreground">{hint}</p>
    </div>
  );
}

function PlatformSetupHints({
  platform,
  currentRedirectUri,
}: {
  platform: string;
  currentRedirectUri: string;
}) {
  const desktopUri = DESKTOP_REDIRECT_URIS[platform];
  const sameAsDesktop =
    Boolean(desktopUri) && desktopUri === currentRedirectUri;

  if (platform === "youtube_shorts") {
    return (
      <div className="space-y-2 text-xs text-muted-foreground">
        <p>
          Create an OAuth client ID (type{" "}
          <span className="text-foreground/90">Desktop</span> or{" "}
          <span className="text-foreground/90">Web</span>) in{" "}
          <a
            href={GOOGLE_CREDENTIALS_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sky-400 hover:underline"
          >
            Google Cloud Console → Credentials
          </a>
          . Paste the client ID and secret below.
        </p>
        {desktopUri && (
          <RedirectUriRow
            label="Desktop redirect URI"
            uri={desktopUri}
            hint="Paste this into Google Authorized redirect URIs for the packaged app."
          />
        )}
        {!sameAsDesktop && currentRedirectUri && (
          <RedirectUriRow
            label="This install's redirect URI"
            uri={currentRedirectUri}
            hint="Use this when configuring a non-desktop or overridden callback."
          />
        )}
        <p>
          Need a walkthrough?{" "}
          <Link
            href={helpHref("/tutorials/TUTORIAL_PUBLISH_YOUTUBE/")}
            className="text-sky-400 hover:underline"
          >
            Publish to YouTube tutorial
          </Link>
          .
        </p>
      </div>
    );
  }

  if (platform === "tiktok") {
    return (
      <div className="space-y-2 text-xs text-muted-foreground">
        <p>
          Register an app and configure Login Kit at{" "}
          <a
            href={TIKTOK_LOGIN_KIT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sky-400 hover:underline"
          >
            TikTok for Developers → Login Kit
          </a>
          , then paste the client key and secret below. In this beta, publish
          lands in inbox/drafts only (not public post).
        </p>
        {desktopUri && (
          <RedirectUriRow
            label="Desktop redirect URI"
            uri={desktopUri}
            hint="Paste this into TikTok Redirect URI for the packaged app."
          />
        )}
        {!sameAsDesktop && currentRedirectUri && (
          <RedirectUriRow
            label="This install's redirect URI"
            uri={currentRedirectUri}
            hint="Use this when configuring a non-desktop or overridden callback."
          />
        )}
        <p>
          Need a walkthrough?{" "}
          <Link
            href={helpHref("/tutorials/TUTORIAL_PUBLISH_YOUTUBE/")}
            className="text-sky-400 hover:underline"
          >
            Publish setup help
          </Link>
          .
        </p>
      </div>
    );
  }

  return null;
}

function PlatformOAuthForm({ app, hasPro }: { app: OAuthAppConfig; hasPro: boolean }) {
  const { push: toast } = useToastSafe();
  const boundAction = updateOAuthAppAction.bind(null, app.platform);
  const [state, formAction] = useActionState(boundAction, initial);

  useEffect(() => {
    if (state.status === "ok") {
      toast(
        "OAuth app saved",
        `${PLATFORM_LABELS[app.platform] ?? app.platform} credentials updated. Connect your account next.`,
      );
    }
  }, [state.status, app.platform, toast]);

  const label = PLATFORM_LABELS[app.platform] ?? app.platform;

  return (
    <form action={formAction} className="space-y-3 rounded-lg border border-border/60 p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-medium">{label}</h3>
        {app.configured ? (
          <span className="text-[10px] uppercase tracking-wide text-emerald-400/90">
            Configured
          </span>
        ) : (
          <span className="text-[10px] uppercase tracking-wide text-amber-400/90">
            Required
          </span>
        )}
      </div>
      <PlatformSetupHints
        platform={app.platform}
        currentRedirectUri={app.redirect_uri}
      />
      <Input
        name="client_id"
        placeholder="OAuth client ID"
        defaultValue={app.client_id}
        disabled={!hasPro}
        required
      />
      <Input
        name="client_secret"
        type="password"
        placeholder="OAuth client secret"
        disabled={!hasPro}
        required
      />
      <Input
        name="redirect_uri"
        placeholder="Redirect URI (optional override)"
        defaultValue={app.redirect_uri}
        disabled={!hasPro}
      />
      {state.status === "error" && state.message && (
        <p className="text-xs text-destructive">{state.message}</p>
      )}
      <Button type="submit" size="sm" disabled={!hasPro}>
        Save {label} app
      </Button>
      {app.configured && (
        <p className="text-xs text-muted-foreground">
          Next:{" "}
          <Link href={DISTRIBUTION_SETTINGS_HREF} className="text-sky-400 hover:underline">
            connect your {label} account
          </Link>
          .
        </p>
      )}
    </form>
  );
}

export function OAuthSetupWizard({ apps, hasPro }: Props) {
  if (apps.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Publish setup</CardTitle>
          <CardDescription>
            No publish platforms are enabled on this install.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Publish setup</CardTitle>
        <CardDescription>
          Add your YouTube and TikTok developer credentials before connecting
          accounts on the Distribution page. See{" "}
          <Link
            href={helpHref("/tutorials/TUTORIAL_PUBLISH_YOUTUBE/")}
            className="text-sky-400 hover:underline"
          >
            the publish tutorial
          </Link>{" "}
          for the short path.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!hasPro && (
          <p className="text-sm text-amber-400/90 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3">
            Pro license required to save OAuth app credentials. Activate a license below.
          </p>
        )}
        {apps.map((app) => (
          <PlatformOAuthForm key={app.platform} app={app} hasPro={hasPro} />
        ))}
      </CardContent>
    </Card>
  );
}

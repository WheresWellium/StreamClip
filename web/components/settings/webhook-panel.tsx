"use client";

import { useEffect, useState } from "react";

import {
  getWebhookSettingsAction,
  updateWebhookSettingsAction,
} from "@/lib/api/actions/settings";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function WebhookPanel({ isAuthenticated }: { isAuthenticated: boolean }) {
  const [url, setUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [configured, setConfigured] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) return;
    void getWebhookSettingsAction().then((res) => {
      if (res.status === "ok" && res.settings) {
        setUrl(res.settings.webhook_url ?? "");
        setConfigured(res.settings.configured);
      }
    });
  }, [isAuthenticated]);

  const save = async (nextUrl: string | null, nextSecret: string | null) => {
    setLoading(true);
    setError(null);
    setMessage(null);
    const res = await updateWebhookSettingsAction(nextUrl, nextSecret);
    if (res.status === "ok" && res.settings) {
      setUrl(res.settings.webhook_url ?? "");
      setSecret("");
      setConfigured(res.settings.configured);
      setMessage(res.settings.configured ? "Webhook saved." : "Webhook removed.");
    } else {
      setError(res.message ?? "Could not save webhook settings.");
    }
    setLoading(false);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Webhooks</CardTitle>
        <CardDescription>
          POST job.completed and publish events to your endpoint. Payloads are
          signed with the secret (X-qClip-Signature).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {!isAuthenticated ? (
          <p className="text-sm text-muted-foreground">Sign in to configure a webhook.</p>
        ) : (
          <>
            <div className="space-y-2">
              <label className="text-xs text-muted-foreground" htmlFor="webhook-url">
                Endpoint URL
              </label>
              <Input
                id="webhook-url"
                placeholder="https://example.com/hooks/qclip"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs text-muted-foreground" htmlFor="webhook-secret">
                Signing secret {configured && "(leave blank to keep current)"}
              </label>
              <Input
                id="webhook-secret"
                type="password"
                placeholder="whsec_…"
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => void save(url.trim() || null, secret.trim() || null)}
                disabled={loading || !url.trim()}
              >
                Save
              </Button>
              {configured && (
                <Button
                  variant="outline"
                  onClick={() => void save(null, null)}
                  disabled={loading}
                >
                  Remove
                </Button>
              )}
            </div>
            {message && <p className="text-xs text-emerald-500">{message}</p>}
            {error && <p className="text-xs text-destructive">{error}</p>}
          </>
        )}
      </CardContent>
    </Card>
  );
}

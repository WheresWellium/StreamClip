"use client";

import { useState, useEffect } from "react";

import {
  activateLicenseAction,
  getLicenseStatusAction,
} from "@/lib/api/actions/license";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToastSafe } from "@/components/providers/toast-provider";
import type { LicenseStatus } from "@/lib/api/client";
import { getLicenseMachineId } from "@/lib/license-machine-id";

export function LicensePanel() {
  const { push: toast } = useToastSafe();
  const [machineId] = useState(() => getLicenseMachineId());
  const [key, setKey] = useState("");
  const [status, setStatus] = useState<LicenseStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showInstallId, setShowInstallId] = useState(false);

  const loadStatus = async () => {
    const result = await getLicenseStatusAction(machineId);
    if (result.status === "ok" && result.license) {
      setStatus(result.license);
    }
  };

  useEffect(() => {
    void loadStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activate = async () => {
    setLoading(true);
    setError(null);
    const result = await activateLicenseAction(key, machineId);
    setLoading(false);
    if (result.status === "error") {
      setError(result.message ?? "Activation failed. Try again.");
      return;
    }
    setStatus(result.license ?? null);
    setKey("");
    toast(
      "License activated",
      `Unlocked: ${(result.license?.capabilities ?? ["studio"]).join(", ") || result.license?.tier || "studio"}.`,
    );
    void loadStatus();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>License</CardTitle>
        <CardDescription>
          Activate a one-time key on this machine. Studio unlocks the clip
          workspace; Publisher and Audio are add-on capabilities on the same app.
          Keys work offline after first activation.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder="SCPRO-XXXX-XXXX-XXXX-XXXX"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            disabled={loading}
          />
          <Button onClick={() => void activate()} disabled={loading || !key.trim()}>
            {loading ? "Activating…" : "Activate"}
          </Button>
          <Button variant="outline" onClick={() => void loadStatus()} disabled={loading}>
            Refresh
          </Button>
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
        {status && (
          <dl className="text-sm grid grid-cols-2 gap-2">
            <dt className="text-muted-foreground">Tier</dt>
            <dd className="uppercase">{status.tier}</dd>
            <dt className="text-muted-foreground">Capabilities</dt>
            <dd className="font-mono text-xs">
              {(status.capabilities && status.capabilities.length > 0
                ? status.capabilities
                : status.active
                  ? ["studio", "publisher"]
                  : []
              ).join(", ") || "—"}
            </dd>
            <dt className="text-muted-foreground">Active</dt>
            <dd>{status.active ? "Yes" : "No"}</dd>
            <dt className="text-muted-foreground">Expires</dt>
            <dd>{status.expires_at ?? "Never (perpetual)"}</dd>
            <dt className="text-muted-foreground">This install</dt>
            <dd>
              {showInstallId ? (
                <span className="font-mono text-xs truncate block">
                  {status.machine_id ?? machineId}
                </span>
              ) : (
                <button
                  type="button"
                  className="text-xs text-sky-400 hover:underline"
                  onClick={() => setShowInstallId(true)}
                >
                  Show details
                </button>
              )}
            </dd>
          </dl>
        )}
      </CardContent>
    </Card>
  );
}

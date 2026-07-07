"use client";

import { useRouter } from "next/navigation";
import * as React from "react";

import {
  disconnectPlatformAction,
  startOAuthAction,
} from "@/lib/api/actions/distribution";
import { ProGateModal } from "@/components/distribution/pro-gate-modal";
import { useToastSafe } from "@/components/providers/toast-provider";
import { Button } from "@/components/ui/button";

type Platform = {
  id: string;
  label: string;
  enabled: boolean;
  connected: boolean;
};

type Connection = {
  id: string;
  platform: string;
  account_label: string;
};

type Props = {
  platforms: Platform[];
  connections: Connection[];
  hasPro: boolean;
};

export function DistributionConnections({
  platforms,
  connections,
  hasPro,
}: Props) {
  const router = useRouter();
  const { push: toast } = useToastSafe();
  const [connecting, setConnecting] = React.useState<string | null>(null);
  const [disconnecting, setDisconnecting] = React.useState<string | null>(null);
  const [proGateOpen, setProGateOpen] = React.useState(false);

  const connByPlatform = Object.fromEntries(connections.map((c) => [c.platform, c]));

  async function handleConnect(platformId: string) {
    if (!hasPro) {
      setProGateOpen(true);
      return;
    }
    setConnecting(platformId);
    try {
      const result = await startOAuthAction(platformId);
      if (result.url) {
        window.location.href = result.url;
        return;
      }
      if (result.error === "login_required") {
        router.push("/login?next=/distribution");
      } else if (result.error === "pro_required") {
        router.push("/distribution?error=pro_required");
      } else {
        toast("Connect failed", result.error ?? "Could not start OAuth.");
      }
    } finally {
      setConnecting(null);
    }
  }
  async function handleDisconnect(connectionId: string) {
    setDisconnecting(connectionId);
    try {
      const result = await disconnectPlatformAction(connectionId);
      if (result.status === "ok") {
        toast("Disconnected", "Platform connection removed.");
        router.refresh();
      } else {
        toast("Disconnect failed", result.message ?? "Could not remove connection.");
      }
    } finally {
      setDisconnecting(null);
    }
  }

  if (platforms.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No distribution platforms are enabled on this install.
      </p>
    );
  }

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2">
      {platforms.map((p) => {
        const conn = connByPlatform[p.id];
        return (
          <div
            key={p.id}
            className="glossy-surface rounded-lg border border-border/60 p-4 space-y-3"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-medium text-sm">{p.label}</h3>
                {conn ? (
                  <p className="text-xs text-emerald-400/90 mt-1">
                    Connected as {conn.account_label}
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground mt-1">Not connected</p>
                )}
              </div>
              {!p.enabled && (
                <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  Soon
                </span>
              )}
            </div>
            {conn ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="w-full"
                disabled={disconnecting === conn.id}
                onClick={() => void handleDisconnect(conn.id)}
              >
                {disconnecting === conn.id ? "Removing…" : "Disconnect"}
              </Button>
            ) : (
              <Button
                type="button"
                size="sm"
                className="w-full"
                disabled={!p.enabled || connecting === p.id}
                onClick={() => void handleConnect(p.id)}
              >
                {connecting === p.id ? "Redirecting…" : hasPro ? "Connect" : "Connect (Pro)"}
              </Button>
            )}
          </div>
        );
      })}
      </div>
      <ProGateModal open={proGateOpen} onClose={() => setProGateOpen(false)} />
    </>
  );
}

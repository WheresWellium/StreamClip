"use client";

import { useEffect, useState } from "react";

import { metaApi, type DeviceProfile, type StorageStatus } from "@/lib/api/client";
import { cn } from "@/lib/utils/format";

function formatBytes(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  const gb = n / (1024 ** 3);
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  const mb = n / (1024 ** 2);
  return `${mb.toFixed(0)} MB`;
}

export function DeviceProfileCard({ className }: { className?: string }) {
  const [profile, setProfile] = useState<DeviceProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await metaApi.deviceProfile();
        if (!cancelled) setProfile(data);
      } catch {
        if (!cancelled) setError("Could not read device profile.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return <p className="text-sm text-muted-foreground">{error}</p>;
  }
  if (!profile) {
    return <p className="text-sm text-muted-foreground">Checking this device…</p>;
  }

  return (
    <div className={cn("space-y-3 rounded-sm border border-white/15 bg-white/[0.03] p-4", className)}>
      <div>
        <p className="text-sm font-medium text-foreground">{profile.recommendation}</p>
        <p className="mt-1 text-sm text-muted-foreground">{profile.recommendation_detail}</p>
      </div>
      <dl className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
        <div>
          <dt className="uppercase tracking-wide opacity-70">CPU</dt>
          <dd className="text-foreground">
            {profile.cpu_model} · {profile.cpu_cores} cores
          </dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide opacity-70">Memory</dt>
          <dd className="text-foreground">
            {profile.ram_total_gb != null ? `${profile.ram_total_gb} GB` : "—"}
          </dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide opacity-70">Free disk</dt>
          <dd className="text-foreground">{profile.disk_free_gb.toFixed(1)} GB</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide opacity-70">Acceleration</dt>
          <dd className="text-foreground">
            {profile.cuda || profile.nvenc || profile.mps
              ? [
                  profile.cuda ? "CUDA" : null,
                  profile.nvenc ? "NVENC" : null,
                  profile.mps ? "Apple GPU" : null,
                ]
                  .filter(Boolean)
                  .join(" · ")
              : "CPU only"}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function StorageStatusCard({ className }: { className?: string }) {
  const [status, setStatus] = useState<StorageStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await metaApi.storageStatus();
        if (!cancelled) setStatus(data);
      } catch {
        if (!cancelled) setError("Could not read storage status.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return <p className="text-sm text-muted-foreground">{error}</p>;
  }
  if (!status) {
    return <p className="text-sm text-muted-foreground">Locating clip storage…</p>;
  }

  if (status.advanced || status.backend !== "local") {
    return (
      <div className={cn("space-y-2 rounded-sm border border-white/15 bg-white/[0.03] p-4", className)}>
        <p className="text-sm font-medium">External / team storage</p>
        <p className="text-sm text-muted-foreground">
          This install uses advanced object storage ({status.backend}). For the
          desktop app, clips are normally saved on this device.
        </p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-3 rounded-sm border border-white/15 bg-white/[0.03] p-4", className)}>
      <div>
        <p className="text-sm font-medium">{status.label}</p>
        <p className="mt-1 break-all font-mono text-xs text-muted-foreground">
          {status.human_root ?? status.root}
        </p>
      </div>
      <dl className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
        <div>
          <dt className="uppercase tracking-wide opacity-70">Used by qClip</dt>
          <dd className="text-foreground">{formatBytes(status.used_bytes)}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide opacity-70">Free on drive</dt>
          <dd className="text-foreground">{formatBytes(status.free_bytes)}</dd>
        </div>
      </dl>
    </div>
  );
}

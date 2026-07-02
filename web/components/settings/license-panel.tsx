"use client";

import { useState, useEffect } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type LicenseStatus = {
  active: boolean;
  tier: string;
  machine_id?: string;
};

async function getMachineId(): Promise<string> {
  const res = await fetch("/api/license/status?machine_id=local");
  if (res.ok) {
    const data = await res.json();
    if (data.machine_id) return data.machine_id;
  }
  return "local";
}

export function LicensePanel() {
  const [key, setKey] = useState("");
  const [machineId, setMachineId] = useState("local");
  const [status, setStatus] = useState<LicenseStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = async (mid: string) => {
    const res = await fetch(`/api/license/status?machine_id=${encodeURIComponent(mid)}`);
    if (res.ok) setStatus(await res.json());
  };

  useEffect(() => {
    void getMachineId().then((mid) => {
      setMachineId(mid);
      void loadStatus(mid);
    });
  }, []);

  const activate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/license/activate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ license_key: key, machine_id: machineId }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.message ?? "Activation failed");
      }
      setStatus({ active: true, tier: (await res.json()).tier, machine_id: machineId });
      setKey("");
      void loadStatus(machineId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Activation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>License</CardTitle>
        <CardDescription>
          Pro tier unlocks higher clip counts and monthly quotas on this install.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder="STREAMCLIP-XXXX-XXXX-XXXX"
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
          <Button onClick={() => void activate()} disabled={loading || !key.trim()}>
            Activate
          </Button>
          <Button variant="outline" onClick={() => void loadStatus(machineId)}>
            Refresh
          </Button>
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
        {status && (
          <dl className="text-sm grid grid-cols-2 gap-2">
            <dt className="text-muted-foreground">Tier</dt>
            <dd>{status.tier}</dd>
            <dt className="text-muted-foreground">Active</dt>
            <dd>{status.active ? "Yes" : "No"}</dd>
            <dt className="text-muted-foreground">Machine</dt>
            <dd className="font-mono text-xs truncate">{status.machine_id}</dd>
          </dl>
        )}
      </CardContent>
    </Card>
  );
}

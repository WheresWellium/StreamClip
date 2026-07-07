"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { authHeaders } from "@/lib/auth/credentials";
import {
  getClientAccessToken,
  getClientDeviceId,
  isDeviceClaimed,
  markDeviceClaimed,
} from "@/lib/auth/client-session";

type Props = {
  deviceId: string;
};

export function ClaimDeviceModal({ deviceId }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(true);
  const [status, setStatus] = useState<"idle" | "claiming" | "done" | "error">("idle");
  const [claimed, setClaimed] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    setOpen(true);
  }, [deviceId]);

  if (!open) return null;

  const handleClaim = async () => {
    setStatus("claiming");
    setErrorMessage(null);
    try {
      const token = getClientAccessToken();
      if (!token) throw new Error("Sign in required");
      const res = await fetch("/api/auth/claim-device", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(token, deviceId ?? getClientDeviceId()),
        },
        body: JSON.stringify({ device_id: deviceId }),
      });
      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(
          typeof payload.message === "string" ? payload.message : "Claim failed",
        );
      }
      const data = await res.json();
      setClaimed(data.jobs_claimed ?? 0);
      setStatus("done");
      markDeviceClaimed();
      router.refresh();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Claim failed");
      setStatus("error");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="glossy-surface max-w-md w-full p-6 space-y-4">
        <h2 className="text-lg font-medium">Claim your local jobs?</h2>
        <p className="text-sm text-muted-foreground">
          You have anonymous jobs on this device. Link them to your account so they
          follow you across sessions.
        </p>
        {status === "done" && (
          <p className="text-sm text-sky-400">
            Linked {claimed} job{claimed === 1 ? "" : "s"} to your account.
          </p>
        )}
        {status === "error" && (
          <p className="text-sm text-destructive">
            {errorMessage ?? "Could not claim jobs. Try again."}
          </p>
        )}
        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={() => setOpen(false)}>
            Skip
          </Button>
          <Button onClick={handleClaim} disabled={status === "claiming" || status === "done"}>
            {status === "claiming" ? "Linking…" : status === "done" ? "Done" : "Link jobs"}
          </Button>
        </div>
      </div>
    </div>
  );
}

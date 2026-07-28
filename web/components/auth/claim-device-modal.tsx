"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiClientError, authApi } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import {
  getClientAccessToken,
  getClientDeviceId,
  markDeviceClaimed,
} from "@/lib/auth/client-session";

type Props = {
  deviceId: string;
};

export function ClaimDeviceModal({ deviceId }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(true);
  const [status, setStatus] = useState<"idle" | "claiming" | "done" | "error">(
    "idle",
  );
  const [claimed, setClaimed] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    setOpen(true);
  }, [deviceId]);

  const handleClaim = async () => {
    setStatus("claiming");
    setErrorMessage(null);
    try {
      const token = getClientAccessToken();
      if (!token)
        throw new Error("Sign in required — log in again, then retry.");
      const resolvedDevice = deviceId ?? getClientDeviceId();
      if (!resolvedDevice)
        throw new Error("Device ID missing — refresh the page and retry.");

      const data = await authApi.claimDevice(resolvedDevice, token);
      setClaimed(data.jobs_claimed ?? 0);
      setStatus("done");
      markDeviceClaimed();
      router.refresh();
    } catch (err) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage(err instanceof Error ? err.message : "Claim failed");
      }
      setStatus("error");
    }
  };

  return (
    <Modal
      open={open}
      onClose={() => setOpen(false)}
      labelledBy="claim-device-title"
      className="w-full max-w-md"
    >
      <div className="glossy-surface w-full p-6 space-y-4">
        <h2 id="claim-device-title" className="text-lg font-medium">
          Claim your local jobs?
        </h2>
        <p className="text-sm text-muted-foreground">
          You have anonymous jobs on this device. Link them to your account so
          they follow you across sessions.
        </p>
        {status === "done" && (
          <p className="text-sm text-sky-400">
            Linked {claimed} job{claimed === 1 ? "" : "s"} to your account.
            {claimed === 0 && (
              <span className="block mt-1 text-muted-foreground">
                No matching anonymous jobs were found for this device.
              </span>
            )}
          </p>
        )}
        {status === "error" && (
          <p className="text-sm text-destructive">
            {errorMessage ?? "Could not claim jobs. Try again."}
          </p>
        )}
        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={() => setOpen(false)}>
            {status === "done" ? "Close" : "Skip"}
          </Button>
          <Button
            onClick={() => void handleClaim()}
            disabled={status === "claiming" || status === "done"}
          >
            {status === "claiming"
              ? "Linking…"
              : status === "done"
                ? "Done"
                : "Link jobs"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

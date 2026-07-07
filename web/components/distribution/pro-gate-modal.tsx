"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";

type Props = {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
};

export function ProGateModal({
  open,
  onClose,
  title = "Pro required",
  description = "Publishing, scheduling, and platform connections require a Pro license or install entitlement.",
}: Props) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4">
      <div
        role="dialog"
        aria-labelledby="pro-gate-title"
        className="glossy-surface max-w-md w-full p-6 space-y-4 border border-border/60"
      >
        <h2 id="pro-gate-title" className="text-lg font-medium">
          {title}
        </h2>
        <p className="text-sm text-muted-foreground">{description}</p>
        <p className="text-xs text-muted-foreground">
          Save to Clip Vault remains available on Free within your tier quota.
        </p>
        <div className="flex gap-2 justify-end">
          <Button type="button" variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button asChild>
            <Link href="/settings?section=license">Open Settings</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}

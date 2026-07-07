"use client";

import { Loader2, ShieldCheck } from "lucide-react";
import * as React from "react";

import { updatePrivacyOptInAction } from "@/lib/api/actions/support";
import { useToastSafe } from "@/components/providers/toast-provider";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type Props = {
  isAuthenticated: boolean;
  initialOptIn: boolean;
};

export function PrivacyPanel({ isAuthenticated, initialOptIn }: Props) {
  const { push: toast } = useToastSafe();
  const [optIn, setOptIn] = React.useState(initialOptIn);
  const [pending, setPending] = React.useState(false);

  async function handleToggle(next: boolean) {
    setPending(true);
    const result = await updatePrivacyOptInAction(next);
    setPending(false);
    if (!result.ok) {
      toast("Could not save", result.message ?? "Try again.");
      return;
    }
    setOptIn(result.optIn ?? next);
    toast(
      next ? "Contribution enabled" : "Contribution disabled",
      next
        ? "Anonymized job data will help improve clip detection."
        : "Your jobs stay entirely on this instance.",
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-sky-400" />
          Privacy &amp; data
        </CardTitle>
        <CardDescription>
          Control whether your completed jobs contribute to model improvement.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-md border border-border/60 bg-background/60 p-3 space-y-2">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={optIn}
              disabled={!isAuthenticated || pending}
              onChange={(e) => handleToggle(e.target.checked)}
              className="mt-0.5 accent-sky-500"
            />
            <span className="text-sm">
              <span className="font-medium flex items-center gap-2">
                Contribute anonymized data to improve StreamClip
                {pending && <Loader2 className="h-3 w-3 animate-spin" />}
              </span>
              <span className="block text-xs text-muted-foreground mt-1">
                When a job finishes, an anonymized bundle (transcript text, clip
                boundaries, and detection scores) is exported for model tuning.
                It never includes your email, source URLs, account identifiers,
                or the video itself. Off by default; you can change this any
                time.
              </span>
            </span>
          </label>
        </div>

        {!isAuthenticated && (
          <p className="text-xs text-muted-foreground">
            Sign in to manage data contribution.
          </p>
        )}

        <div className="text-xs text-muted-foreground space-y-1.5">
          <p className="font-medium text-foreground">How your data is handled</p>
          <ul className="list-disc list-inside space-y-1">
            <li>
              Jobs, clips, and transcripts stay on your self-hosted instance
              unless you publish externally or configure webhooks.
            </li>
            <li>
              Your account is never deleted by license events — deactivation
              only disables sign-in.
            </li>
            <li>
              Contributed bundles live under an internal storage prefix and are
              reviewed before any training use.
            </li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}

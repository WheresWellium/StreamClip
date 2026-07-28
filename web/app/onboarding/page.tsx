"use client";

import { useEffect, useState } from "react";

import { metaApi } from "@/lib/api/client";
import type { StreamClipMeta } from "@/lib/api/meta-types";
import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";
import { Button } from "@/components/ui/button";
import { normalizeStreamClipMeta } from "@/lib/normalize-meta";
import { userFacingErrorMessage } from "@/lib/help/user-errors";

const SAMPLE_URL =
  process.env.NEXT_PUBLIC_ONBOARDING_SAMPLE_URL ??
  "https://www.youtube.com/watch?v=jNQXAC9IVRw";

export default function OnboardingPage() {
  const [meta, setMeta] = useState<StreamClipMeta | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoadError(null);
    void metaApi
      .meta()
      .then((raw) => {
        if (!cancelled) setMeta(normalizeStreamClipMeta(raw));
      })
      .catch((err) => {
        if (!cancelled) {
          setMeta(null);
          setLoadError(
            userFacingErrorMessage(
              err instanceof Error ? err.message : null,
              null,
              "Studio API is unreachable. Start Docker / the sidecar and retry.",
            ),
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [retryKey]);

  if (loadError) {
    return (
      <div className="mx-auto max-w-xl space-y-4 py-16 text-center">
        <p role="alert" className="text-sm text-destructive">
          {loadError}
        </p>
        <Button type="button" onClick={() => setRetryKey((k) => k + 1)}>
          Retry
        </Button>
      </div>
    );
  }

  if (!meta) {
    return <p className="text-sm text-muted-foreground py-8">Loading…</p>;
  }

  return <OnboardingWizard sampleUrl={SAMPLE_URL} meta={meta} />;
}

"use client";

import { useEffect, useState } from "react";

import { metaApi } from "@/lib/api/client";
import type { StreamClipMeta } from "@/lib/api/meta-types";
import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";
import { normalizeStreamClipMeta } from "@/lib/normalize-meta";

const SAMPLE_URL =
  process.env.NEXT_PUBLIC_ONBOARDING_SAMPLE_URL ??
  "https://www.youtube.com/watch?v=jNQXAC9IVRw";

export default function OnboardingPage() {
  const [meta, setMeta] = useState<StreamClipMeta | null>(null);

  useEffect(() => {
    let cancelled = false;
    void metaApi.meta().then((raw) => {
      if (!cancelled) {
        setMeta(normalizeStreamClipMeta(raw));
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!meta) {
    return <p className="text-sm text-muted-foreground py-8">Loading…</p>;
  }

  return <OnboardingWizard sampleUrl={SAMPLE_URL} meta={meta} />;
}

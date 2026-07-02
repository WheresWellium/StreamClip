import { metaApi } from "@/lib/api/client";
import type { StreamClipMeta } from "@/lib/api/meta-types";
import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";

const SAMPLE_URL =
  process.env.STREAMCLIP_ONBOARDING_SAMPLE_URL ??
  "https://www.youtube.com/watch?v=jNQXAC9IVRw";

import { normalizeStreamClipMeta } from "@/lib/normalize-meta";

export default async function OnboardingPage() {
  const rawMeta = await metaApi.meta();
  const meta = normalizeStreamClipMeta(rawMeta);

  return <OnboardingWizard sampleUrl={SAMPLE_URL} meta={meta} />;
}

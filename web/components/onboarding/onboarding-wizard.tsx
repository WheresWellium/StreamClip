"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";

import { completeOnboardingAction } from "@/lib/api/actions/onboarding";
import { markOnboardingComplete } from "@/lib/auth/client-session";
import { HealthChecklist, type StackHealthSnapshot } from "@/components/onboarding/health-checklist";
import { CreateJobForm } from "@/components/jobs/create-job-form";
import { Button } from "@/components/ui/button";
import { metaApi } from "@/lib/api/client";
import type { StreamClipMeta } from "@/lib/api/meta-types";

type Step = "welcome" | "health" | "storage" | "ready" | "account";

const STEPS: Step[] = ["welcome", "health", "storage", "ready", "account"];

function stepIndex(step: Step): number {
  return STEPS.indexOf(step);
}

type Props = {
  sampleUrl: string;
  meta: StreamClipMeta;
};

export function OnboardingWizard({ sampleUrl, meta }: Props) {
  const router = useRouter();
  const [step, setStep] = useState<Step>("welcome");
  const [health, setHealth] = useState<StackHealthSnapshot | null>(null);
  const [checking, setChecking] = useState(false);

  const runHealthCheck = useCallback(async () => {
    setChecking(true);
    try {
      const data = await metaApi.stackHealth();
      setHealth(data);
    } catch {
      setHealth({ status: "error", checks: {}, worker: false });
    } finally {
      setChecking(false);
    }
  }, []);

  const finish = async () => {
    markOnboardingComplete();
    await completeOnboardingAction();
    router.push("/settings?section=get-started");
    router.refresh();
  };

  const next = () => {
    const idx = stepIndex(step);
    if (idx < STEPS.length - 1) {
      const nextStep = STEPS[idx + 1];
      if (nextStep === "health") void runHealthCheck();
      setStep(nextStep);
    } else {
      void finish();
    }
  };

  return (
    <div className="max-w-xl mx-auto space-y-8 py-8">
      <div className="flex gap-2">
        {STEPS.map((s) => (
          <div
            key={s}
            className={`h-1 flex-1 rounded ${stepIndex(s) <= stepIndex(step) ? "bg-sky-400" : "bg-white/10"}`}
          />
        ))}
      </div>

      {step === "welcome" && (
        <section className="space-y-4">
          <h1 className="text-2xl font-semibold">Welcome to Jet Stream</h1>
          <p className="text-muted-foreground">
            The clip studio for any length of footage — auto-reframe to any ratio,
            caption and overlay in one pass, then rank what wins before you publish.
          </p>
        </section>
      )}

      {step === "health" && (
        <section className="space-y-4">
          <h1 className="text-2xl font-semibold">Stack health</h1>
          <p className="text-sm text-muted-foreground">
            We verify database, storage, and workers before your first clip job.
          </p>
          <HealthChecklist
            data={health}
            loading={checking}
            onRetry={() => void runHealthCheck()}
          />
        </section>
      )}

      {step === "storage" && (
        <section className="space-y-4">
          <h1 className="text-2xl font-semibold">Storage</h1>
          <p className="text-muted-foreground">
            Clips and uploads are stored locally (MinIO) or your configured S3 bucket.
            Ensure Docker volumes have enough free space for your typical VOD length.
          </p>
        </section>
      )}

      {step === "ready" && (
        <section className="space-y-4">
          <h1 className="text-2xl font-semibold">Create your first clip</h1>
          <p className="text-sm text-muted-foreground">
            Try the sample URL below or drag a video file onto the upload zone.
          </p>
          <CreateJobForm
            meta={meta}
            templates={[]}
            isAuthenticated={false}
            defaultSourceUrl={sampleUrl}
          />
        </section>
      )}

      {step === "account" && (
        <section className="space-y-4">
          <h1 className="text-2xl font-semibold">Optional account</h1>
          <p className="text-muted-foreground">
            Sign in to sync jobs across devices, save templates, and configure webhooks.
            You can skip and stay anonymous on this device.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => void finish()}>
              Skip for now
            </Button>
            <Button onClick={() => router.push("/register")}>Create account</Button>
            <Button variant="secondary" onClick={() => router.push("/settings?section=get-started")}>
              Open activation checklist
            </Button>
          </div>
        </section>
      )}

      {step !== "account" && step !== "ready" && (
        <Button onClick={next}>Continue</Button>
      )}
      {step === "ready" && (
        <Button onClick={next}>Finish setup</Button>
      )}
    </div>
  );
}

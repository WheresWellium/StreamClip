"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function DistributionRedirect() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const qs = new URLSearchParams({ section: "distribution" });
    const connected = searchParams.get("connected");
    const error = searchParams.get("error");
    if (connected) qs.set("connected", connected);
    if (error) qs.set("error", error);
    router.replace(`/settings?${qs.toString()}`);
  }, [searchParams, router]);

  return (
    <p className="text-sm text-muted-foreground text-center py-12">
      Redirecting to settings…
    </p>
  );
}

export default function DistributionPage() {
  return (
    <Suspense
      fallback={
        <p className="text-sm text-muted-foreground text-center py-12">
          Loading…
        </p>
      }
    >
      <DistributionRedirect />
    </Suspense>
  );
}

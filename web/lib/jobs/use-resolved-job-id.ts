"use client";

import { useEffect, useState } from "react";
import { useParams, usePathname } from "next/navigation";

import { resolveJobId } from "@/lib/jobs/job-route-id";

export type ResolvedJobId = {
  /** Null until the client has resolved the browser path (static `_` shells). */
  jobId: string | null;
  /** False during SSR / first paint before window path is applied. */
  ready: boolean;
};

/** Job id for overview/clips pages under static-export `_` shells. */
export function useResolvedJobId(): ResolvedJobId {
  const params = useParams<{ id?: string }>();
  const pathname = usePathname() ?? "";
  const [jobId, setJobId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const path =
      typeof window !== "undefined" ? window.location.pathname : pathname;
    setJobId(resolveJobId(params?.id, path));
    setReady(true);
  }, [params?.id, pathname]);

  return { jobId, ready };
}

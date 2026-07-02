"use client";

import * as React from "react";

export type PublishProgressEvent = {
  publish_job_id: string;
  stage: string;
  progress: number;
  message: string;
  status: string;
  external_url?: string;
};

export function usePublishProgress(publishJobId: string | null) {
  const [event, setEvent] = React.useState<PublishProgressEvent | null>(null);
  const [terminal, setTerminal] = React.useState(false);

  React.useEffect(() => {
    if (!publishJobId) return;

    const source = new EventSource(
      `/api/distribution/publish-jobs/${publishJobId}/progress`,
    );

    const onProgress = (e: MessageEvent<string>) => {
      try {
        const data = JSON.parse(e.data) as PublishProgressEvent;
        setEvent(data);
        if (data.status === "done" || data.status === "error") {
          setTerminal(true);
          source.close();
        }
      } catch {
        /* ignore malformed frames */
      }
    };

    source.addEventListener("progress", onProgress);
    source.addEventListener("done", onProgress);
    source.addEventListener("error", onProgress);

    return () => {
      source.close();
    };
  }, [publishJobId]);

  return { event, terminal };
}

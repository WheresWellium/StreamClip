"use client";

import * as React from "react";

import { jobsApi } from "@/lib/api/client";
import type { ClipFeedExtra, ClipFeedItem, ProgressEvent } from "@/lib/api/types";
import { useJobProgress } from "@/lib/api/use-job-progress";

const POLL_INTERVAL_MS = 8000;

function feedStatusFromEvent(event: ClipFeedExtra["event"]): ClipFeedItem["feedStatus"] {
  if (event === "clip_done") return "done";
  if (event === "clip_processing") return "processing";
  return "discovered";
}

function mergeClipFeedItem(
  prev: ClipFeedItem | undefined,
  extra: ClipFeedExtra,
): ClipFeedItem {
  const nextStatus = feedStatusFromEvent(extra.event);
  const statusRank = { discovered: 0, processing: 1, done: 2 };
  const feedStatus =
    prev && statusRank[prev.feedStatus] > statusRank[nextStatus]
      ? prev.feedStatus
      : nextStatus;

  return {
    clip_id: extra.clip_id,
    rank: extra.rank,
    title: extra.title?.trim() || prev?.title || null,
    feedStatus,
  };
}

function isClipFeedExtra(value: unknown): value is ClipFeedExtra {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.clip_id === "string" &&
    typeof v.rank === "number" &&
    (v.event === "clip_discovered" ||
      v.event === "clip_processing" ||
      v.event === "clip_done")
  );
}

function clipsFromJob(job: Awaited<ReturnType<typeof jobsApi.get>>): ClipFeedItem[] {
  return job.clips.map((clip) => ({
    clip_id: clip.id,
    rank: clip.rank,
    title: clip.title ?? null,
    feedStatus: clip.status === "done" ? "done" : "processing",
  }));
}

function mergeMaps(
  feed: Map<string, ClipFeedItem>,
  fromJob: ClipFeedItem[],
): ClipFeedItem[] {
  const merged = new Map(feed);
  for (const item of fromJob) {
    const prev = merged.get(item.clip_id);
    if (!prev) {
      merged.set(item.clip_id, item);
      continue;
    }
    const statusRank = { discovered: 0, processing: 1, done: 2 };
    merged.set(item.clip_id, {
      ...prev,
      title: prev.title || item.title,
      feedStatus:
        statusRank[item.feedStatus] > statusRank[prev.feedStatus]
          ? item.feedStatus
          : prev.feedStatus,
    });
  }
  return Array.from(merged.values()).sort((a, b) => a.rank - b.rank);
}

export function useJobClipFeed(
  jobId: string | null,
  options: { enabled?: boolean; initialClips?: ClipFeedItem[] } = {},
) {
  const { enabled = true, initialClips = [] } = options;
  const progress = useJobProgress(jobId, { enabled });
  const [feed, setFeed] = React.useState<Map<string, ClipFeedItem>>(() => {
    const map = new Map<string, ClipFeedItem>();
    for (const clip of initialClips) {
      map.set(clip.clip_id, clip);
    }
    return map;
  });

  const lastEvent: ProgressEvent | null =
    "lastEvent" in progress ? (progress.lastEvent ?? null) : null;

  React.useEffect(() => {
    const extra = lastEvent?.extra;
    if (!isClipFeedExtra(extra)) return;
    setFeed((prev) => {
      const next = new Map(prev);
      next.set(extra.clip_id, mergeClipFeedItem(prev.get(extra.clip_id), extra));
      return next;
    });
  }, [lastEvent]);

  React.useEffect(() => {
    if (!jobId || !enabled) return;

    let cancelled = false;

    const poll = async () => {
      try {
        const job = await jobsApi.get(jobId);
        if (cancelled) return;
        const fromJob = clipsFromJob(job);
        if (fromJob.length === 0) return;
        setFeed((prev) => {
          const merged = mergeMaps(prev, fromJob);
          return new Map(merged.map((item) => [item.clip_id, item]));
        });
      } catch {
        /* keep feed */
      }
    };

    void poll();
    const timer = window.setInterval(() => void poll(), POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [jobId, enabled]);

  const clips = React.useMemo(
    () => Array.from(feed.values()).sort((a, b) => a.rank - b.rank),
    [feed],
  );

  return {
    clips,
    progressStatus: progress.status,
    connected:
      progress.status === "open" ||
      progress.status === "done" ||
      progress.status === "reconnecting" ||
      progress.status === "polling",
  };
}

"use client";

import { useEffect, useState } from "react";

/**
 * Rotate through tip strings without noisy screen-reader announcements.
 * Visual-only; status aria text stays on the primary loading message.
 */
export function useRotatingTips(
  tips: string[],
  intervalMs: number,
  enabled: boolean,
): string | null {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    setIndex(0);
  }, [tips]);

  useEffect(() => {
    if (!enabled || tips.length <= 1) return;
    const id = window.setInterval(() => {
      setIndex((i) => (i + 1) % tips.length);
    }, Math.max(1200, intervalMs));
    return () => window.clearInterval(id);
  }, [enabled, tips, intervalMs]);

  if (!tips.length) return null;
  return tips[index] ?? tips[0] ?? null;
}

"use client";

import { useEffect, useMemo, useState } from "react";

interface StatusTextProps {
  message: string;
  tips: string[];
  tipIntervalMs: number;
  announceText: string;
  reducedMotion: boolean;
}

export function StatusText({
  message,
  tips,
  tipIntervalMs,
  announceText,
  reducedMotion,
}: StatusTextProps) {
  const safeTips = useMemo(
    () => tips.filter((t) => t.trim().length > 0),
    [tips],
  );
  const [tipIndex, setTipIndex] = useState(0);
  const [swapping, setSwapping] = useState(false);

  useEffect(() => {
    setTipIndex(0);
    setSwapping(false);
  }, [safeTips]);

  useEffect(() => {
    if (safeTips.length <= 1 || reducedMotion) return;

    let swapTimer: number | undefined;
    const id = window.setInterval(() => {
      setSwapping(true);
      swapTimer = window.setTimeout(() => {
        setTipIndex((i) => (i + 1) % safeTips.length);
        setSwapping(false);
      }, 200);
    }, tipIntervalMs);

    return () => {
      window.clearInterval(id);
      if (swapTimer !== undefined) window.clearTimeout(swapTimer);
    };
  }, [safeTips, tipIntervalMs, reducedMotion]);

  const tip = safeTips[tipIndex] ?? "";

  return (
    <div className="sc-loading__status-row">
      <p className="sc-loading__status" aria-hidden="true">
        <span>{message}</span>
        <span className="sc-loading__ellipsis" />
      </p>
      {tip ? (
        <p
          className={
            swapping ? "sc-loading__tip sc-loading__tip--swap" : "sc-loading__tip"
          }
          aria-hidden="true"
        >
          {tip}
        </p>
      ) : null}
      {/* Single polite live region — avoid announcing every ellipsis tick */}
      <p
        className="sc-loading__sr"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {announceText}
      </p>
    </div>
  );
}

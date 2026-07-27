"use client";

import { useEffect, useState } from "react";

import type { ReducedMotionBehavior } from "../types";

/**
 * Resolves whether nonessential motion should be simplified.
 */
export function usePrefersReducedMotion(
  behavior: ReducedMotionBehavior = "respect",
): boolean {
  const [reduced, setReduced] = useState(behavior === "force-reduced");

  useEffect(() => {
    if (behavior === "ignore") {
      setReduced(false);
      return;
    }
    if (behavior === "force-reduced") {
      setReduced(true);
      return;
    }

    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReduced(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, [behavior]);

  return reduced;
}

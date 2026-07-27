"use client";

import { useEffect, useState } from "react";

/**
 * Preload / decode a cover image without blocking first paint.
 * Returns load status so the UI can fall back to the gradient.
 */
export function useCoverArtPreload(src: string | null | undefined): {
  loaded: boolean;
  failed: boolean;
} {
  const [loaded, setLoaded] = useState(!src);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!src) {
      setLoaded(true);
      setFailed(false);
      return;
    }

    let cancelled = false;
    setLoaded(false);
    setFailed(false);

    const img = new Image();
    img.decoding = "async";
    img.onload = () => {
      if (cancelled) return;
      const finish = () => {
        if (!cancelled) setLoaded(true);
      };
      if (typeof img.decode === "function") {
        void img.decode().then(finish).catch(finish);
      } else {
        finish();
      }
    };
    img.onerror = () => {
      if (cancelled) return;
      setFailed(true);
      setLoaded(false);
    };
    img.src = src;

    return () => {
      cancelled = true;
      img.onload = null;
      img.onerror = null;
    };
  }, [src]);

  return { loaded, failed };
}

"use client";

import { useEffect, useState, type CSSProperties } from "react";

interface CoverArtProps {
  src?: string;
  focalX: number;
  focalY: number;
}

/**
 * Cover / hero background. Falls back to a polished CSS gradient if the
 * image fails or is omitted.
 */
export function CoverArt({ src, focalX, focalY }: CoverArtProps) {
  const [failed, setFailed] = useState(!src);

  useEffect(() => {
    if (!src) {
      setFailed(true);
      return;
    }

    let cancelled = false;
    setFailed(false);

    const img = new Image();
    img.decoding = "async";
    img.onload = () => {
      if (!cancelled) setFailed(false);
    };
    img.onerror = () => {
      if (!cancelled) setFailed(true);
    };
    img.src = src;

    return () => {
      cancelled = true;
    };
  }, [src]);

  const style: CSSProperties = {
    ["--sc-load-focal" as string]: `${focalX}% ${focalY}%`,
    ...(src && !failed
      ? { backgroundImage: `url("${src}")` }
      : undefined),
  };

  return (
    <div
      className={
        src && !failed
          ? "sc-loading__cover"
          : "sc-loading__cover sc-loading__cover--fallback"
      }
      style={style}
      aria-hidden="true"
    />
  );
}

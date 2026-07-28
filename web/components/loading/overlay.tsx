import type { CSSProperties } from "react";

interface OverlayProps {
  color: string;
  opacity: number;
}

/** Readability gradient + vignette. Decorative — hidden from AT. */
export function LoadingOverlay({ color, opacity }: OverlayProps) {
  const style = {
    ["--sc-load-overlay" as string]: color,
    ["--sc-load-overlay-opacity" as string]: String(opacity),
  } as CSSProperties;

  return (
    <>
      <div className="sc-loading__overlay" style={style} aria-hidden="true" />
      <div className="sc-loading__vignette" aria-hidden="true" />
      <div className="sc-loading__grain" aria-hidden="true" />
      <div className="sc-loading__glow" aria-hidden="true" />
    </>
  );
}

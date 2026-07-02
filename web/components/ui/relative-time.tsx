"use client";

import * as React from "react";

import { formatRelativeTime } from "@/lib/utils/format";

/**
 * Relative timestamps are computed client-side only to avoid SSR/client drift
 * (e.g. "41m ago" vs "42m ago" between server render and hydration).
 */
export function RelativeTime({ iso }: { iso: string }) {
  const [label, setLabel] = React.useState<string>("");

  React.useEffect(() => {
    const update = () => setLabel(formatRelativeTime(iso));
    update();
    const id = window.setInterval(update, 60_000);
    return () => window.clearInterval(id);
  }, [iso]);

  return (
    <span suppressHydrationWarning className={label ? undefined : "text-muted-foreground/50"}>
      {label || "…"}
    </span>
  );
}

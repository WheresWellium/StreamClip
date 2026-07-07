"use client";

/**
 * Phase 2b-ii — platform safe-zone guides for vertical video.
 *
 * Bands mark where TikTok / YouTube Shorts UI covers the frame:
 * top ~10% (account row), bottom ~22% (caption + actions), right ~14%
 * (like/comment/share rail). Content and burned captions should stay
 * inside the remaining area.
 */

type Props = {
  visible: boolean;
};

export function SafeZoneOverlay({ visible }: Props) {
  if (!visible) return null;
  return (
    <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
      {/* Top band — account / following row */}
      <div className="absolute inset-x-0 top-0 h-[10%] bg-red-500/15 border-b border-dashed border-red-400/50" />
      {/* Bottom band — caption text + action bar */}
      <div className="absolute inset-x-0 bottom-0 h-[22%] bg-red-500/15 border-t border-dashed border-red-400/50" />
      {/* Right rail — like / comment / share */}
      <div className="absolute right-0 top-[10%] bottom-[22%] w-[14%] bg-red-500/10 border-l border-dashed border-red-400/40" />
      <span className="absolute left-1.5 top-[11%] text-[9px] uppercase tracking-wide text-red-300/90">
        Safe area
      </span>
    </div>
  );
}

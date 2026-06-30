import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(secs: number | null | undefined): string {
  if (secs == null || !isFinite(secs)) return "—";
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = Math.floor(secs % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}

export function formatScore(score: number): string {
  return (score * 100).toFixed(0);
}

export const emotionColors: Record<string, string> = {
  hype: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  rage: "bg-red-500/10 text-red-400 border-red-500/20",
  funny: "bg-green-500/10 text-green-400 border-green-500/20",
  clutch: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  fail: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  weird: "bg-fuchsia-500/10 text-fuchsia-400 border-fuchsia-500/20",
  neutral: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
};

export const statusColors: Record<string, string> = {
  queued: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  ingesting: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  transcribing: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  detecting: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  processing: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  done: "bg-green-500/10 text-green-400 border-green-500/20",
  error: "bg-red-500/10 text-red-400 border-red-500/20",
  cancelled: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  pending: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
};

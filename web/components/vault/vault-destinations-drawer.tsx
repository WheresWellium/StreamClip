"use client";

import { Calendar, Loader2, Send } from "lucide-react";
import * as React from "react";

import {
  getDistributionContextAction,
  publishVaultClipAction,
  scheduleVaultClipAction,
} from "@/lib/api/actions/distribution";
import { ProGateModal } from "@/components/distribution/pro-gate-modal";
import { useToastSafe } from "@/components/providers/toast-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/form";
import { HelpTip } from "@/components/ui/help-tip";
import type { VaultClip } from "@/lib/api/client";
import { cn } from "@/lib/utils/format";

type Tab = "publish" | "schedule";

type Props = {
  clip: VaultClip;
  open: boolean;
  onClose: () => void;
};

export function VaultDestinationsDrawer({ clip, open, onClose }: Props) {
  const { push: toast } = useToastSafe();
  const [tab, setTab] = React.useState<Tab>("publish");
  const [submitting, setSubmitting] = React.useState(false);
  const [platform, setPlatform] = React.useState("youtube_shorts");
  const [title, setTitle] = React.useState(clip.title || "");
  const [description, setDescription] = React.useState(clip.hook || "");
  const [scheduledAt, setScheduledAt] = React.useState("");
  const [proGateOpen, setProGateOpen] = React.useState(false);
  const [ctx, setCtx] = React.useState<
    Awaited<ReturnType<typeof getDistributionContextAction>> | null
  >(null);
  const [loadingCtx, setLoadingCtx] = React.useState(false);

  React.useEffect(() => {
    if (!open) return;
    setTitle(clip.title || "");
    setDescription(clip.hook || "");
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose, clip.title, clip.hook]);

  React.useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoadingCtx(true);
    void getDistributionContextAction().then((data) => {
      if (!cancelled) {
        setCtx(data);
        const connected = data.platforms.find((p) => p.connected && p.enabled);
        if (connected) setPlatform(connected.id);
      }
      if (!cancelled) setLoadingCtx(false);
    });
    return () => {
      cancelled = true;
    };
  }, [open]);

  if (!open) return null;

  const connectedPlatforms =
    ctx?.platforms.filter((p) => p.enabled && p.connected) ?? [];
  const canPublish = clip.status === "ready" && ctx?.hasPro;

  async function handlePublish() {
    if (!ctx?.hasPro) {
      setProGateOpen(true);
      return;
    }
    if (!canPublish) return;
    setSubmitting(true);
    try {
      const result = await publishVaultClipAction(clip.id, platform, title, description);
      if (result.status === "ok") {
        toast("Publish queued", "Track progress in Distribution.");
        onClose();
      } else {
        toast("Publish failed", result.message ?? "Could not publish.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSchedule() {
    if (!ctx?.hasPro) {
      setProGateOpen(true);
      return;
    }
    if (!canPublish || !scheduledAt) return;
    setSubmitting(true);
    try {
      const iso = new Date(scheduledAt).toISOString();
      const result = await scheduleVaultClipAction(
        clip.id,
        platform,
        iso,
        title,
        description,
      );
      if (result.status === "ok") {
        toast("Scheduled", "Your clip will publish at the chosen time.");
        onClose();
      } else {
        toast("Schedule failed", result.message ?? "Could not schedule.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <button
        type="button"
        className="fixed inset-0 z-40 bg-black/50"
        aria-label="Close destinations"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-labelledby="vault-destinations-title"
        className="fixed right-0 top-0 z-50 h-full w-full max-w-md glossy-surface border-l border-border/60 shadow-xl flex flex-col animate-fade-in"
      >
        <div className="p-4 border-b border-border/60">
          <h2 id="vault-destinations-title" className="text-sm font-medium">
            Publish from Vault
          </h2>
          <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
            {clip.title || "Untitled"}
          </p>
          <div className="flex mt-3 rounded-md border border-border/60 overflow-hidden text-xs">
            {(
              [
                { id: "publish" as const, label: "Publish now", icon: Send },
                { id: "schedule" as const, label: "Schedule", icon: Calendar },
              ] as const
            ).map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => setTab(id)}
                className={cn(
                  "flex-1 flex items-center justify-center gap-1 px-2 py-2 min-h-[44px]",
                  tab === id ? "bg-sky-600/25 text-sky-100" : "text-muted-foreground",
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          {clip.status !== "ready" && (
            <p className="text-xs text-amber-400/90">
              Wait until this vault clip finishes copying before publishing.
            </p>
          )}
          {loadingCtx ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : !ctx?.hasPro ? (
            <div className="space-y-3 text-sm text-muted-foreground">
              <p>Publishing requires Pro.</p>
              <Button type="button" variant="outline" className="w-full" onClick={() => setProGateOpen(true)}>
                Learn about Pro
              </Button>
            </div>
          ) : connectedPlatforms.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Connect YouTube or TikTok in Distribution before publishing.
            </p>
          ) : (
            <>
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground" htmlFor="vault-platform">
                  Platform
                </label>
                <select
                  id="vault-platform"
                  className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm"
                  value={platform}
                  onChange={(e) => setPlatform(e.target.value)}
                >
                  {connectedPlatforms.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                    </option>
                  ))}
                </select>
                {platform === "tiktok" && (
                  <p className="text-xs text-muted-foreground">
                    TikTok uploads land in your TikTok app inbox — open the
                    notification there to finish posting.
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground" htmlFor="vault-pub-title">
                  Title
                </label>
                <Input
                  id="vault-pub-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={100}
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground" htmlFor="vault-pub-desc">
                  Description
                </label>
                <textarea
                  id="vault-pub-desc"
                  className="w-full min-h-[80px] rounded-md border border-border/60 bg-background px-3 py-2 text-sm"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              {tab === "schedule" && (
                <div className="space-y-2">
                  <div className="flex items-center gap-1">
                    <label className="text-xs text-muted-foreground" htmlFor="vault-sched-at">
                      Publish at
                    </label>
                    {platform === "tiktok" && (
                      <HelpTip
                        label="TikTok schedule help"
                        content="TikTok has no native schedule API in v1 — Jet Stream posts at this time."
                      />
                    )}
                  </div>
                  <Input
                    id="vault-sched-at"
                    type="datetime-local"
                    value={scheduledAt}
                    onChange={(e) => setScheduledAt(e.target.value)}
                  />
                </div>
              )}
              <Button
                className="w-full"
                disabled={!canPublish || submitting || (tab === "schedule" && !scheduledAt)}
                onClick={tab === "publish" ? handlePublish : handleSchedule}
              >
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : tab === "publish" ? (
                  <Send className="h-4 w-4" />
                ) : (
                  <Calendar className="h-4 w-4" />
                )}
                {tab === "publish" ? "Publish now" : "Schedule publish"}
              </Button>
            </>
          )}
        </div>

        <div className="p-4 border-t border-border/60">
          <Button variant="outline" className="w-full" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>

      <ProGateModal open={proGateOpen} onClose={() => setProGateOpen(false)} />
    </>
  );
}

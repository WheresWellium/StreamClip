"use client";

import { Loader2, MessageCircle, X } from "lucide-react";
import { usePathname } from "next/navigation";
import * as React from "react";

import { useToastSafe } from "@/components/providers/toast-provider";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/form";
import { submitBetaFeedbackAction } from "@/lib/api/actions/support";
import type { BetaFeedbackArea, BetaFeedbackTopic } from "@/lib/api/client";
import { cn } from "@/lib/utils/format";

const INTENTS: {
  id: BetaFeedbackTopic;
  label: string;
  hint: string;
}[] = [
  {
    id: "help",
    label: "I'm stuck",
    hint: "Something blocked me from finishing a task",
  },
  {
    id: "question",
    label: "How do I…",
    hint: "I need to understand a step or setting",
  },
  {
    id: "idea",
    label: "Feature idea",
    hint: "A change that would make the product better",
  },
  {
    id: "praise",
    label: "What worked",
    hint: "Something that felt great — keep it",
  },
  {
    id: "other",
    label: "Something else",
    hint: "Feedback that doesn't fit the options above",
  },
];

const AREAS: { id: BetaFeedbackArea; label: string }[] = [
  { id: "getting_started", label: "Getting started" },
  { id: "ingest", label: "New job / ingest" },
  { id: "clipping", label: "Clipping & moments" },
  { id: "captions", label: "Captions & transcript" },
  { id: "reframe", label: "Reframe / vertical" },
  { id: "vault", label: "Vault & library" },
  { id: "distribution", label: "Publishing" },
  { id: "license_billing", label: "License / billing" },
  { id: "performance", label: "Speed / performance" },
  { id: "ui", label: "UI / navigation" },
  { id: "other", label: "Other" },
];

const GUIDANCE: Record<
  BetaFeedbackTopic,
  { tip: string; placeholder: string }
> = {
  help: {
    tip: "Say what you were trying to do, where you got stuck, and what you already tried. If a job failed or crashed, use Report a bug instead — it routes faster.",
    placeholder:
      "I was trying to…\nI got stuck when…\nI already tried…\nWhat I expected…",
  },
  question: {
    tip: "Ask one concrete question. Name the screen or setting if you can.",
    placeholder: "On [page/setting], how do I…?\nGoal: I want to…",
  },
  idea: {
    tip: "Describe the problem first, then the idea. Who is it for?",
    placeholder:
      "Problem today…\nIdea…\nWho it helps…\nNice-to-have vs must-have…",
  },
  praise: {
    tip: "Call out what felt smooth so we don't break it in the next build.",
    placeholder: "What worked well…\nWhy it mattered…",
  },
  other: {
    tip: "Anything else for the beta team — keep it specific if you can.",
    placeholder: "What's on your mind?",
  },
};

type BetaFeedbackDialogProps = {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
};

function areaFromPath(pathname: string): BetaFeedbackArea | null {
  if (pathname.startsWith("/jobs/new")) return "ingest";
  if (pathname.startsWith("/jobs")) return "clipping";
  if (pathname.startsWith("/vault")) return "vault";
  if (pathname.startsWith("/settings")) return "license_billing";
  if (pathname.startsWith("/help")) return "getting_started";
  if (pathname === "/" || pathname.startsWith("/docs")) return "getting_started";
  return null;
}

function supportDeliveryToast(
  toast: (title: string, description?: string) => void,
  opsNotification?: string,
) {
  if (opsNotification === "queued") {
    toast("Feedback sent", "Thanks — the team will follow up.");
    return;
  }
  toast("Feedback saved", "Saved — we'll review it.");
}

export function BetaFeedbackDialog({
  open: controlledOpen,
  onOpenChange,
}: BetaFeedbackDialogProps = {}) {
  const pathname = usePathname();
  const { push: toast } = useToastSafe();

  const [internalOpen, setInternalOpen] = React.useState(false);
  const open = controlledOpen ?? internalOpen;
  const setOpen = onOpenChange ?? setInternalOpen;
  const showTrigger = controlledOpen === undefined;

  const [pending, setPending] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState("");
  const [topic, setTopic] = React.useState<BetaFeedbackTopic>("help");
  const [area, setArea] = React.useState<BetaFeedbackArea | null>(null);

  const guidance = GUIDANCE[topic];

  React.useEffect(() => {
    if (open) {
      setArea(areaFromPath(pathname));
    }
  }, [open, pathname]);

  function reset() {
    setMessage("");
    setTopic("help");
    setArea(null);
    setError(null);
  }

  function openDialog() {
    setArea(areaFromPath(pathname));
    setOpen(true);
  }

  function closeDialog() {
    setOpen(false);
  }

  async function handleSubmit() {
    if (!area) {
      setError("Pick the part of StreamClip this is about.");
      return;
    }
    setPending(true);
    setError(null);
    const result = await submitBetaFeedbackAction({
      message,
      topic,
      area,
      environment: {
        page: pathname,
        user_agent: navigator.userAgent,
        viewport: `${window.innerWidth}x${window.innerHeight}`,
      },
    });
    setPending(false);
    if (!result.ok) {
      setError(result.message ?? "Could not send feedback.");
      return;
    }
    closeDialog();
    reset();
    supportDeliveryToast(toast, result.opsNotification);
  }

  return (
    <>
      {showTrigger && (
        <button
          type="button"
          onClick={openDialog}
          className="inline-flex items-center gap-1 px-2 py-1 rounded-sm text-xs text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Beta feedback"
          title="Beta feedback"
        >
          <MessageCircle className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Beta feedback</span>
        </button>
      )}

      {open && (
        <div
          className="fixed inset-0 z-50 grid place-items-center p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Beta feedback"
        >
          <button
            type="button"
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            aria-label="Close"
            onClick={closeDialog}
          />
          <div className="relative z-10 flex max-h-[min(90vh,720px)] w-full max-w-lg flex-col overflow-hidden rounded-lg border border-border/60 bg-card shadow-2xl">
            <header className="flex shrink-0 items-center justify-between border-b border-border/60 px-4 py-3">
              <div className="flex items-center gap-2">
                <MessageCircle className="h-4 w-4 text-violet-400" />
                <p className="text-sm font-medium">Beta feedback</p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={closeDialog}
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </Button>
            </header>

            <div className="space-y-4 overflow-y-auto px-4 py-4">
              <p className="text-xs text-muted-foreground">
                Tell us what kind of note this is and which part of the product it
                touches — that routes it to the right beta owner.
              </p>

              <div className="space-y-1.5">
                <Label>What kind of note?</Label>
                <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                  {INTENTS.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => {
                        setTopic(item.id);
                        setError(null);
                      }}
                      className={cn(
                        "rounded-md border px-2.5 py-2 text-left transition-colors",
                        topic === item.id
                          ? "border-violet-400/60 bg-violet-400/15 text-foreground"
                          : "border-border/60 text-muted-foreground hover:text-foreground",
                      )}
                      aria-pressed={topic === item.id}
                    >
                      <span className="block text-xs font-medium text-foreground">
                        {item.label}
                      </span>
                      <span className="mt-0.5 block text-[11px] leading-snug text-muted-foreground">
                        {item.hint}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <Label>About which part?</Label>
                <div className="flex flex-wrap gap-1.5">
                  {AREAS.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => {
                        setArea(item.id);
                        setError(null);
                      }}
                      className={cn(
                        "rounded-md border px-2 py-1 text-xs transition-colors",
                        area === item.id
                          ? "border-violet-400/60 bg-violet-400/15 text-foreground"
                          : "border-border/60 text-muted-foreground hover:text-foreground",
                      )}
                      aria-pressed={area === item.id}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>

              <p className="rounded-md border border-border/50 bg-muted/40 px-3 py-2 text-[11px] leading-relaxed text-muted-foreground">
                {guidance.tip}
              </p>

              <div className="space-y-1.5">
                <Label htmlFor="feedback-message">Your message</Label>
                <textarea
                  id="feedback-message"
                  value={message}
                  onChange={(e) => {
                    setMessage(e.target.value);
                    setError(null);
                  }}
                  rows={6}
                  maxLength={5000}
                  placeholder={guidance.placeholder}
                  className={cn(
                    "flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
                    "shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                  )}
                />
              </div>

              {error && (
                <p className="text-xs text-destructive" role="alert">
                  {error}
                </p>
              )}
            </div>

            <footer className="flex shrink-0 justify-end gap-2 border-t border-border/60 bg-muted/30 px-4 py-3">
              <Button
                type="button"
                variant="outline"
                disabled={pending}
                onClick={closeDialog}
              >
                Cancel
              </Button>
              <Button
                type="button"
                disabled={pending || !area || message.trim().length < 10}
                onClick={() => void handleSubmit()}
              >
                {pending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <MessageCircle className="h-3.5 w-3.5" />
                )}
                Send feedback
              </Button>
            </footer>
          </div>
        </div>
      )}
    </>
  );
}

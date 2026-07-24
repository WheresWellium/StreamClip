"use client";

import { MessageCircle, Loader2, X } from "lucide-react";
import { usePathname } from "next/navigation";
import * as React from "react";

import { submitBetaFeedbackAction } from "@/lib/api/actions/support";
import { useToastSafe } from "@/components/providers/toast-provider";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/form";
import { cn } from "@/lib/utils/format";

const TOPICS = [
  { id: "help", label: "Need help" },
  { id: "question", label: "Question" },
  { id: "idea", label: "Idea" },
  { id: "other", label: "Other" },
] as const;

type Topic = (typeof TOPICS)[number]["id"];

type BetaFeedbackDialogProps = {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
};

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
  const [topic, setTopic] = React.useState<Topic>("help");

  function reset() {
    setMessage("");
    setTopic("help");
    setError(null);
  }

  async function handleSubmit() {
    setPending(true);
    setError(null);
    const result = await submitBetaFeedbackAction({
      message,
      topic,
      environment: {
        page: pathname,
        user_agent: navigator.userAgent,
      },
    });
    setPending(false);
    if (!result.ok) {
      setError(result.message ?? "Could not send feedback.");
      return;
    }
    setOpen(false);
    reset();
    supportDeliveryToast(toast, result.opsNotification);
  }

  return (
    <>
      {showTrigger && (
        <button
          type="button"
          onClick={() => setOpen(true)}
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
            onClick={() => setOpen(false)}
          />
          <div className="relative z-10 w-full max-w-lg rounded-lg border border-border/60 bg-card shadow-2xl">
            <header className="flex items-center justify-between border-b border-border/60 px-4 py-3">
              <div className="flex items-center gap-2">
                <MessageCircle className="h-4 w-4 text-violet-400" />
                <p className="text-sm font-medium">Beta feedback</p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => setOpen(false)}
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </Button>
            </header>

            <div className="px-4 py-4 space-y-4">
              <p className="text-xs text-muted-foreground">
                Questions, ideas, or stuck on setup? Send a note to the StreamClip beta team.
              </p>

              <div className="space-y-1.5">
                <Label>Topic</Label>
                <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
                  {TOPICS.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setTopic(item.id)}
                      className={cn(
                        "rounded-md border px-2 py-1.5 text-xs transition-colors",
                        topic === item.id
                          ? "border-violet-400/60 bg-violet-400/15 text-foreground"
                          : "border-border/60 text-muted-foreground hover:text-foreground",
                      )}
                      aria-pressed={topic === item.id}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="feedback-message">Your message</Label>
                <textarea
                  id="feedback-message"
                  value={message}
                  onChange={(e) => {
                    setMessage(e.target.value);
                    setError(null);
                  }}
                  rows={5}
                  maxLength={5000}
                  placeholder="What can we help with? Include steps if something failed."
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

            <footer className="border-t border-border/60 bg-muted/30 px-4 py-3 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                disabled={pending}
                onClick={() => setOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="button"
                className="bg-violet-600 hover:bg-violet-700 text-white"
                disabled={pending || message.trim().length < 10}
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

"use client";

import { Bug, Loader2, X } from "lucide-react";
import { usePathname } from "next/navigation";
import * as React from "react";

import { submitBugReportAction } from "@/lib/api/actions/support";
import { useToastSafe } from "@/components/providers/toast-provider";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/form";
import { Modal } from "@/components/ui/modal";
import { parseJobIdFromPathname } from "@/lib/jobs/job-route-id";
import { cn } from "@/lib/utils/format";

const CATEGORIES: { id: string; label: string }[] = [
  { id: "ingest", label: "Ingest" },
  { id: "transcription", label: "Transcription" },
  { id: "captions", label: "Captions" },
  { id: "reframe", label: "Reframe" },
  { id: "overlays", label: "Overlays" },
  { id: "vault", label: "Vault" },
  { id: "distribution", label: "Distribution" },
  { id: "license_billing", label: "License / Billing" },
  { id: "performance", label: "Performance" },
  { id: "ui", label: "UI" },
  { id: "other", label: "Other" },
];

const SEVERITIES = ["low", "medium", "high", "critical"] as const;
type Severity = (typeof SEVERITIES)[number];

type BugReportDialogProps = {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  /** Prefill the message textarea when the dialog opens. */
  defaultMessage?: string;
  /** Prefill category chips when the dialog opens. */
  defaultCategories?: string[];
  /** Prefill severity when the dialog opens. */
  defaultSeverity?: Severity;
};

/** Pull a job id out of /jobs/[id]... paths to pre-fill the report. */
function jobIdFromPath(pathname: string): string | null {
  return parseJobIdFromPathname(pathname);
}

export function BugReportDialog({
  open: controlledOpen,
  onOpenChange,
  defaultMessage = "",
  defaultCategories,
  defaultSeverity = "medium",
}: BugReportDialogProps = {}) {
  const pathname = usePathname();
  const { push: toast } = useToastSafe();

  const [internalOpen, setInternalOpen] = React.useState(false);
  const open = controlledOpen ?? internalOpen;
  const setOpen = onOpenChange ?? setInternalOpen;
  const showTrigger = controlledOpen === undefined;
  const [pending, setPending] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState(defaultMessage);
  const [categories, setCategories] = React.useState<string[]>(
    () => defaultCategories ?? [],
  );
  const [severity, setSeverity] = React.useState<Severity>(defaultSeverity);
  const [includeJob, setIncludeJob] = React.useState(true);

  const currentJobId = jobIdFromPath(pathname);

  React.useEffect(() => {
    if (!open) return;
    if (defaultMessage) setMessage(defaultMessage);
    if (defaultCategories?.length) setCategories(defaultCategories);
    setSeverity(defaultSeverity);
  }, [open, defaultMessage, defaultCategories, defaultSeverity]);

  function toggleCategory(id: string) {
    setCategories((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    );
    setError(null);
  }

  function reset() {
    setMessage("");
    setCategories([]);
    setSeverity("medium");
    setIncludeJob(true);
    setError(null);
  }

  async function handleSubmit() {
    setPending(true);
    setError(null);
    const result = await submitBugReportAction({
      message,
      categories,
      severity,
      jobId: includeJob ? currentJobId : null,
      environment: {
        page: pathname,
        user_agent: navigator.userAgent,
        viewport: `${window.innerWidth}x${window.innerHeight}`,
      },
    });
    setPending(false);
    if (!result.ok) {
      setError(result.message ?? "Could not submit the report.");
      return;
    }
    setOpen(false);
    reset();
    if (
      result.emailNotification === "queued" ||
      result.opsNotification === "queued"
    ) {
      toast("Bug report sent", "Thanks — we'll take a look.");
    } else {
      toast(
        "Saved on this device only",
        "We cannot see local reports yet — open a GitHub beta bug so we get it.",
      );
    }
  }

  return (
    <>
      {showTrigger && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="inline-flex items-center gap-1 px-2 py-1 rounded-sm text-xs text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Report a bug"
          title="Report a bug"
        >
          <Bug className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Report a bug</span>
        </button>
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        label="Report a bug"
        className="w-full max-w-lg"
        overlayClassName="bg-black/50"
      >
        <div className="flex max-h-[min(90vh,720px)] w-full flex-col overflow-hidden rounded-lg border border-border/60 bg-card shadow-2xl">
          <header className="flex shrink-0 items-center justify-between border-b border-border/60 px-4 py-3">
            <div className="flex items-center gap-2">
              <Bug className="h-4 w-4 text-sky-400" />
              <p className="text-sm font-medium">Report a bug</p>
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

          <div className="px-4 py-4 space-y-4 overflow-y-auto">
            <div className="space-y-1.5">
              <Label>What&apos;s affected? (pick all that apply)</Label>
              <div className="flex flex-wrap gap-1.5">
                {CATEGORIES.map((cat) => {
                  const selected = categories.includes(cat.id);
                  return (
                    <button
                      key={cat.id}
                      type="button"
                      onClick={() => toggleCategory(cat.id)}
                      className={cn(
                        "rounded-full border px-2.5 py-1 text-xs transition-colors",
                        selected
                          ? "border-sky-400/60 bg-sky-400/15 text-sky-700 dark:text-sky-300"
                          : "border-border/60 text-muted-foreground hover:border-border hover:text-foreground",
                      )}
                      aria-pressed={selected}
                    >
                      {cat.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Severity</Label>
              <div className="grid grid-cols-4 gap-1.5">
                {SEVERITIES.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setSeverity(s)}
                    className={cn(
                      "rounded-md border px-2 py-1.5 text-xs capitalize transition-colors",
                      severity === s
                        ? "border-sky-400/60 bg-sky-400/15 text-foreground"
                        : "border-border/60 text-muted-foreground hover:text-foreground",
                    )}
                    aria-pressed={severity === s}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="bug-message">What happened?</Label>
              <textarea
                id="bug-message"
                value={message}
                onChange={(e) => {
                  setMessage(e.target.value);
                  setError(null);
                }}
                rows={5}
                maxLength={5000}
                placeholder="Steps to reproduce, what you expected, and what actually happened…"
                className={cn(
                  "flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
                  "shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                )}
              />
            </div>

            {currentJobId && (
              <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeJob}
                  onChange={(e) => setIncludeJob(e.target.checked)}
                  className="accent-sky-500"
                />
                Attach current job ({currentJobId.slice(0, 8)}…) to this report
              </label>
            )}

            {error && (
              <p className="text-xs text-destructive" role="alert">
                {error}
              </p>
            )}
          </div>

          <footer className="shrink-0 border-t border-border/60 bg-muted/30 px-4 py-3 flex justify-end gap-2">
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
              className="bg-sky-600 hover:bg-sky-700 text-white"
              disabled={
                pending || message.trim().length < 10 || categories.length === 0
              }
              onClick={handleSubmit}
            >
              {pending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Bug className="h-3.5 w-3.5" />
              )}
              Send report
            </Button>
          </footer>
        </div>
      </Modal>
    </>
  );
}

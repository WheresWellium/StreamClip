"use client";

import { Sparkles } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { jobsApi } from "@/lib/api/client";
import { updateJobTitleAction } from "@/lib/api/actions/jobs";
import { getClientAccessToken } from "@/lib/auth/client-session";

type Suggestion = {
  rank: number;
  title: string;
  hook: string;
  confidence: number;
};

type Props = {
  jobId: string;
  disabled?: boolean;
};

export function TitleSuggestionsPanel({ jobId, disabled }: Props) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState<number | null>(null);

  async function loadSuggestions() {
    const token = getClientAccessToken();
    setLoading(true);
    setError(null);
    try {
      const res = await jobsApi.titleSuggestions(jobId, token);
      setSuggestions(res.suggestions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load suggestions");
    } finally {
      setLoading(false);
    }
  }

  async function applyTitle(title: string, rank: number) {
    setApplying(rank);
    setError(null);
    const result = await updateJobTitleAction(jobId, title);
    setApplying(null);
    if (!result.ok) {
      setError(result.message ?? "Could not apply title");
      return;
    }
    router.refresh();
  }

  return (
    <div className="rounded-lg border border-border/60 bg-card/40 p-4 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-medium">Title suggestions</p>
          <p className="text-xs text-muted-foreground">
            AI-generated hooks — apply one or edit manually above.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={disabled || loading}
          onClick={() => void loadSuggestions()}
        >
          <Sparkles className="h-3.5 w-3.5 mr-1.5" />
          {loading ? "Generating…" : suggestions ? "Refresh" : "Suggest titles"}
        </Button>
      </div>

      {error ? <p className="text-xs text-destructive">{error}</p> : null}

      {suggestions && suggestions.length > 0 ? (
        <ul className="space-y-2">
          {suggestions.map((s) => (
            <li
              key={s.rank}
              className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 rounded-md border border-border/50 bg-background/40 px-3 py-2"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium">{s.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{s.hook}</p>
              </div>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                className="shrink-0"
                disabled={applying !== null}
                onClick={() => void applyTitle(s.title, s.rank)}
              >
                {applying === s.rank ? "Applying…" : "Use title"}
              </Button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

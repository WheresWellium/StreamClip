"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { BookOpen, ExternalLink } from "lucide-react";

import {
  DOCS_BASE,
  HELP_TOPICS,
  docsAbsoluteUrl,
  helpHref,
  resolveHelpDocsPath,
} from "@/lib/docs";
import { cn } from "@/lib/utils/format";

/**
 * Embeds the henna docs page (download + how to use) inside the app.
 */
export function DocsViewer() {
  const searchParams = useSearchParams();
  const docsPath = resolveHelpDocsPath(searchParams.get("path"));
  const iframeSrc = docsAbsoluteUrl(docsPath);

  return (
    <div className="flex min-h-[min(78vh,820px)] flex-col gap-4 lg:flex-row">
      <aside className="flex w-full shrink-0 flex-col gap-3 lg:w-56">
        <div>
          <h1 className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            <BookOpen className="h-4 w-4 text-sky-400" aria-hidden="true" />
            Help
          </h1>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            Download qClip, then follow the steps to make a clip.
          </p>
        </div>

        <nav className="flex flex-col gap-1" aria-label="Help sections">
          <Link
            href="/help"
            className={cn(
              "rounded-md border px-3 py-2 text-left text-sm transition-colors",
              docsPath === "/"
                ? "border-sky-400/50 bg-sky-400/10 text-foreground"
                : "border-transparent text-muted-foreground hover:border-border/60 hover:bg-muted/40 hover:text-foreground",
            )}
          >
            Start here
          </Link>
          {HELP_TOPICS.map((topic) => {
            const active = docsPath === topic.docsPath;
            return (
              <Link
                key={topic.id}
                href={helpHref(topic.docsPath)}
                className={cn(
                  "rounded-md border px-3 py-2 text-left text-sm transition-colors",
                  active
                    ? "border-sky-400/50 bg-sky-400/10 text-foreground"
                    : "border-transparent text-muted-foreground hover:border-border/60 hover:bg-muted/40 hover:text-foreground",
                )}
              >
                {topic.label}
              </Link>
            );
          })}
        </nav>

        <a
          href={iframeSrc}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-sky-400"
        >
          <ExternalLink className="h-3 w-3" aria-hidden="true" />
          Open in browser
        </a>
        <p className="text-[10px] text-muted-foreground/80">
          {DOCS_BASE.replace(/^https?:\/\//, "")}
        </p>
      </aside>

      <div className="min-h-[min(70vh,760px)] flex-1 overflow-hidden rounded-lg border border-border/60 bg-card shadow-sm">
        <iframe
          key={iframeSrc}
          src={iframeSrc}
          title="qClip help"
          className="h-full min-h-[min(70vh,760px)] w-full border-0 bg-background"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox"
        />
      </div>
    </div>
  );
}

"use client";

import { Bug, CircleHelp, ExternalLink, MessageCircle } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { BetaFeedbackDialog } from "@/components/support/beta-feedback-dialog";
import { BugReportDialog } from "@/components/support/bug-report-dialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const DOCS_BASE = "https://streamclip-henna.vercel.app";

const DOC_LINKS = [
  { href: `${DOCS_BASE}/BETA_TESTER_QUICKSTART/`, label: "Quickstart" },
  { href: `${DOCS_BASE}/tutorials/TUTORIAL_INSTALL/`, label: "Install guide" },
  { href: `${DOCS_BASE}/tutorials/TUTORIAL_FIRST_JOB/`, label: "First job" },
  { href: `${DOCS_BASE}/tutorials/TUTORIAL_TROUBLESHOOTING/`, label: "Troubleshooting" },
  { href: `${DOCS_BASE}/BETA_KNOWN_ISSUES/`, label: "Known issues" },
] as const;

/** Consolidated help + support menu — one header slot instead of seven. */
export function HeaderHelpMenu() {
  const [feedbackOpen, setFeedbackOpen] = React.useState(false);
  const [bugOpen, setBugOpen] = React.useState(false);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
            aria-label="Help and support"
            tooltip="Help, docs, and support"
          >
            <CircleHelp className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-52">
          <DropdownMenuLabel>Documentation</DropdownMenuLabel>
          {DOC_LINKS.map(({ href, label }) => (
            <DropdownMenuItem key={href} asChild>
              <Link
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between"
              >
                {label}
                <ExternalLink className="h-3 w-3 text-muted-foreground" />
              </Link>
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuLabel>Contact</DropdownMenuLabel>
          <DropdownMenuItem
            onSelect={() => {
              setFeedbackOpen(true);
            }}
          >
            <MessageCircle className="h-4 w-4" />
            Beta feedback
          </DropdownMenuItem>
          <DropdownMenuItem
            onSelect={() => {
              setBugOpen(true);
            }}
          >
            <Bug className="h-4 w-4" />
            Report a bug
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <BetaFeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} />
      <BugReportDialog open={bugOpen} onOpenChange={setBugOpen} />
    </>
  );
}

"use client";

import { Bug, CircleHelp, MessageCircle } from "lucide-react";
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
import { HELP_TOPICS, helpHref } from "@/lib/docs";

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
          {HELP_TOPICS.map(({ id, label, docsPath }) => (
            <DropdownMenuItem key={id} asChild>
              <Link href={helpHref(docsPath)}>{label}</Link>
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

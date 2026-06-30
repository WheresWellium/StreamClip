"use client";

import Link from "next/link";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function HeaderNav() {
  return (
    <nav className="flex items-center gap-4 text-sm">
      <Tooltip>
        <TooltipTrigger asChild>
          <Link
            href="/"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Jobs
          </Link>
        </TooltipTrigger>
        <TooltipContent>
          View all clip jobs and create a new one from the home page.
        </TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <a
            href="/docs"
            className="text-muted-foreground hover:text-foreground transition-colors"
            target="_blank"
            rel="noreferrer"
          >
            API
          </a>
        </TooltipTrigger>
        <TooltipContent>
          Open the REST API reference (OpenAPI) in a new tab.
        </TooltipContent>
      </Tooltip>
    </nav>
  );
}

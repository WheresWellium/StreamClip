"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function BackToJobsLink() {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Link
          href="/jobs"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          All jobs
        </Link>
      </TooltipTrigger>
      <TooltipContent>Return to the job list.</TooltipContent>
    </Tooltip>
  );
}

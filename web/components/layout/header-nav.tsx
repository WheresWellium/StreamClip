"use client";

import Link from "next/link";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

type Props = {
  isAuthenticated?: boolean;
};

export function HeaderNav({ isAuthenticated = false }: Props) {
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
        <TooltipContent>View all clip jobs on the dashboard.</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <Link
            href="/#create"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            New clip
          </Link>
        </TooltipTrigger>
        <TooltipContent>Create a new clip job from URL or upload.</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <Link
            href="/vault"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Vault
          </Link>
        </TooltipTrigger>
        <TooltipContent>Saved clips library — publish or schedule later.</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <Link
            href="/distribution"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Distribution
          </Link>
        </TooltipTrigger>
        <TooltipContent>Connect platforms and manage publish queue.</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <Link
            href="/settings"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Settings
          </Link>
        </TooltipTrigger>
        <TooltipContent>Profile, webhooks, retention, and license.</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <Link
            href={isAuthenticated ? "/settings" : "/login"}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Account
          </Link>
        </TooltipTrigger>
        <TooltipContent>
          {isAuthenticated ? "Manage your account" : "Sign in or register"}
        </TooltipContent>
      </Tooltip>
    </nav>
  );
}

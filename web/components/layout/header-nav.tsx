"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { User } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils/format";

type Props = {
  isAuthenticated?: boolean;
};

const NAV_LINKS = [
  { href: "/jobs", label: "Jobs", tip: "Pipeline runs and progress." },
  { href: "/vault", label: "Vault", tip: "Saved clips — publish or schedule." },
  { href: "/settings", label: "Settings", tip: "License, distribution, and account." },
] as const;

function isActive(pathname: string, href: string) {
  if (href === "/jobs") {
    return pathname === "/" || pathname === "/jobs" || pathname.startsWith("/jobs/");
  }
  if (href === "/settings") {
    return pathname === "/settings" || pathname.startsWith("/settings/") || pathname === "/distribution";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function HeaderNav({ isAuthenticated = false }: Props) {
  const pathname = usePathname();

  return (
    <nav className="flex items-center gap-1 sm:gap-2 text-sm min-w-0">
      {NAV_LINKS.map(({ href, label, tip }) => (
        <Tooltip key={href}>
          <TooltipTrigger asChild>
            <Link
              href={href}
              className={cn(
                "px-2.5 py-1 rounded-sm transition-colors",
                isActive(pathname, href)
                  ? "text-foreground bg-frame/10"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {label}
            </Link>
          </TooltipTrigger>
          <TooltipContent>{tip}</TooltipContent>
        </Tooltip>
      ))}

      <div className="ml-1 sm:ml-2 flex items-center gap-1.5 shrink-0">
        <Button asChild size="sm" variant="default" tooltip="Create a clip job">
          <Link href="/jobs/new">New job</Link>
        </Button>

        <Tooltip>
          <TooltipTrigger asChild>
            <Link
              href={isAuthenticated ? "/settings" : "/login"}
              className={cn(
                "inline-flex h-8 w-8 items-center justify-center rounded-sm transition-colors",
                pathname === "/login" || pathname === "/register"
                  ? "text-foreground bg-frame/10"
                  : "text-muted-foreground hover:text-foreground hover:bg-frame/5",
              )}
              aria-label={isAuthenticated ? "Account settings" : "Sign in"}
            >
              <User className="h-4 w-4" />
            </Link>
          </TooltipTrigger>
          <TooltipContent>
            {isAuthenticated ? "Account settings" : "Sign in or register"}
          </TooltipContent>
        </Tooltip>
      </div>
    </nav>
  );
}

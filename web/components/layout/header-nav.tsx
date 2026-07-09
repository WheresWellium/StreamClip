"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils/format";

type Props = {
  isAuthenticated?: boolean;
};

const LINKS = [
  { href: "/", label: "Home", tip: "Dashboard and quick actions." },
  { href: "/jobs", label: "Jobs", tip: "All pipeline runs and progress." },
  { href: "/jobs/new", label: "New job", tip: "Create a clip job from URL or upload." },
  { href: "/vault", label: "Vault", tip: "Saved clips — publish or schedule later." },
  { href: "/settings", label: "Settings", tip: "Profile, license, distribution, API, and integrations." },
] as const;

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  if (href === "/jobs") return pathname === "/jobs" || pathname.startsWith("/jobs/");
  if (href === "/settings") {
    return pathname === "/settings" || pathname.startsWith("/settings/") || pathname === "/distribution";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function HeaderNav({ isAuthenticated = false }: Props) {
  const pathname = usePathname();

  return (
    <nav className="flex items-center gap-1 sm:gap-3 text-sm flex-wrap justify-end">
      {LINKS.map(({ href, label, tip }) => (
        <Tooltip key={href}>
          <TooltipTrigger asChild>
            <Link
              href={href}
              className={cn(
                "px-2 py-1 rounded-sm transition-colors",
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
      <Tooltip>
        <TooltipTrigger asChild>
          <Link
            href={isAuthenticated ? "/settings" : "/login"}
            className={cn(
              "px-2 py-1 rounded-sm transition-colors ml-1 border border-frame/20",
              pathname === "/login" || pathname === "/register"
                ? "text-foreground bg-frame/10"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {isAuthenticated ? "Profile" : "Sign in"}
          </Link>
        </TooltipTrigger>
        <TooltipContent>
          {isAuthenticated ? "Manage your account" : "Sign in or register"}
        </TooltipContent>
      </Tooltip>
    </nav>
  );
}

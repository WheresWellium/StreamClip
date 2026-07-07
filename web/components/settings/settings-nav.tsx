"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { cn } from "@/lib/utils/format";

export type SettingsSection =
  | "account"
  | "get-started"
  | "license"
  | "distribution"
  | "integrations"
  | "privacy"
  | "advanced";

const SECTIONS: { id: SettingsSection; label: string }[] = [
  { id: "account", label: "Account" },
  { id: "get-started", label: "Get started" },
  { id: "license", label: "License" },
  { id: "distribution", label: "Distribution" },
  { id: "integrations", label: "Integrations" },
  { id: "privacy", label: "Privacy & data" },
  { id: "advanced", label: "Advanced" },
];

export function SettingsNav() {
  const searchParams = useSearchParams();
  const active = (searchParams.get("section") as SettingsSection | null) ?? "account";

  return (
    <nav className="space-y-0.5" aria-label="Settings sections">
      {SECTIONS.map(({ id, label }) => {
        const href = id === "account" ? "/settings" : `/settings?section=${id}`;
        const isActive = active === id;
        return (
          <Link
            key={id}
            href={href}
            className={cn(
              "block rounded-sm px-3 py-2 text-sm transition-colors",
              isActive
                ? "bg-sky-400/10 text-sky-400 font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-frame/5",
            )}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

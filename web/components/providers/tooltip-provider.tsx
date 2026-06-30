"use client";

import { TooltipProvider } from "@/components/ui/tooltip";

export function AppTooltipProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <TooltipProvider delayDuration={200} skipDelayDuration={100}>
      {children}
    </TooltipProvider>
  );
}

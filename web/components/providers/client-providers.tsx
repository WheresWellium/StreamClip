"use client";

import { AppTooltipProvider } from "@/components/providers/tooltip-provider";
import { ToastProvider } from "@/components/providers/toast-provider";
import { TokenRefreshProvider } from "@/components/providers/token-refresh";

/**
 * Single client boundary for app-wide UI providers.
 * Keeps tooltip + toast context available to all routes.
 */
export function ClientProviders({ children }: { children: React.ReactNode }) {
  return (
    <AppTooltipProvider>
      <ToastProvider>
        <TokenRefreshProvider>{children}</TokenRefreshProvider>
      </ToastProvider>
    </AppTooltipProvider>
  );
}

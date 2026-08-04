"use client";

import * as Toast from "@radix-ui/react-toast";
import * as React from "react";

type ToastMessage = { id: string; title: string; description?: string };

const ToastContext = React.createContext<{
  push: (title: string, description?: string) => void;
} | null>(null);

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return ctx;
}

/** Non-throwing variant for components that may render before providers hydrate. */
export function useToastSafe() {
  const ctx = React.useContext(ToastContext);
  return React.useMemo(
    () => ctx ?? { push: (_title: string, _description?: string) => {} },
    [ctx],
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = React.useState(false);
  const [messages, setMessages] = React.useState<ToastMessage[]>([]);

  const push = React.useCallback((title: string, description?: string) => {
    const id = crypto.randomUUID();
    setMessages((m) => [...m, { id, title, description }]);
    setOpen(true);
  }, []);

  // Stable identity — a fresh `{ push }` each render retriggers effects that
  // depend on useToastSafe() and can cause React #185 (max update depth).
  const value = React.useMemo(() => ({ push }), [push]);

  const current = messages[messages.length - 1];

  return (
    <ToastContext.Provider value={value}>
      <Toast.Provider swipeDirection="right">
        {children}
        <Toast.Root
          open={open}
          onOpenChange={setOpen}
          className="fixed bottom-4 right-4 z-50 rounded-md border border-border bg-card px-4 py-3 shadow-lg data-[state=open]:animate-in"
        >
          {current && (
            <>
              <Toast.Title className="text-sm font-medium">{current.title}</Toast.Title>
              {current.description && (
                <Toast.Description className="text-xs text-muted-foreground mt-1">
                  {current.description}
                </Toast.Description>
              )}
            </>
          )}
          <Toast.Close className="sr-only">Dismiss</Toast.Close>
        </Toast.Root>
        <Toast.Viewport className="fixed bottom-0 right-0 z-[100] flex max-h-screen w-full flex-col-reverse gap-2 p-4 sm:max-w-[420px]" />
      </Toast.Provider>
    </ToastContext.Provider>
  );
}

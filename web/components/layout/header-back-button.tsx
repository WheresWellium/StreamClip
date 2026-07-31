"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { canNavigateUp, parentPath } from "@/lib/navigation/parent-path";

const STACK_KEY = "qclip.navStack";
const MAX_STACK = 40;

function readStack(): string[] {
  try {
    const raw = sessionStorage.getItem(STACK_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((p): p is string => typeof p === "string");
  } catch {
    return [];
  }
}

function writeStack(stack: string[]): void {
  try {
    sessionStorage.setItem(STACK_KEY, JSON.stringify(stack));
  } catch {
    /* private mode / quota — Back still uses parentPath */
  }
}

/**
 * Always-visible Back control for desktop (no browser chrome) and web.
 * Prefers in-session history; falls back to hierarchical parent routes.
 */
export function HeaderBackButton() {
  const router = useRouter();
  const pathname = usePathname() || "/";
  const skippingPush = useRef(false);
  const [enabled, setEnabled] = useState(() => canNavigateUp(pathname));

  useEffect(() => {
    const stack = readStack();

    if (skippingPush.current) {
      skippingPush.current = false;
    } else if (stack[stack.length - 1] !== pathname) {
      stack.push(pathname);
      if (stack.length > MAX_STACK) {
        stack.splice(0, stack.length - MAX_STACK);
      }
      writeStack(stack);
    }

    setEnabled(stack.length >= 2 || canNavigateUp(pathname));
  }, [pathname]);

  const goBack = () => {
    const stack = readStack();
    if (stack.length >= 2) {
      stack.pop();
      const prev = stack[stack.length - 1] ?? "/";
      writeStack(stack);
      skippingPush.current = true;
      setEnabled(stack.length >= 2 || canNavigateUp(prev));
      router.push(prev);
      return;
    }

    const fallback = parentPath(pathname);
    if (fallback !== pathname) {
      skippingPush.current = true;
      router.push(fallback);
    }
  };

  const goBackRef = useRef(goBack);
  goBackRef.current = goBack;

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!(event.altKey && event.key === "ArrowLeft")) return;
      const target = event.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT" ||
          target.isContentEditable)
      ) {
        return;
      }
      event.preventDefault();
      goBackRef.current();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className="shrink-0 gap-1.5 px-2 text-muted-foreground hover:text-foreground"
      disabled={!enabled}
      aria-label="Go back"
      tooltip={enabled ? "Go back" : "You're on the home screen"}
      onClick={goBack}
    >
      <ArrowLeft className="h-4 w-4" aria-hidden="true" />
      <span className="hidden sm:inline">Back</span>
    </Button>
  );
}

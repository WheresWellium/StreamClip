"use client";

import * as React from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/utils/format";

type ModalProps = {
  open: boolean;
  onClose: () => void;
  /** Accessible name — omit when `labelledBy` points at a visible heading. */
  label?: string;
  labelledBy?: string;
  /** Panel classes — width and max-height belong here. */
  className?: string;
  /** Scroll-container classes — override `z-50` when stacking over a drawer. */
  rootClassName?: string;
  overlayClassName?: string;
  closeOnOverlayClick?: boolean;
  children: React.ReactNode;
};

/**
 * Centered modal shell.
 *
 * Rendered through a portal on `document.body`: any ancestor with a transform,
 * filter, or backdrop-filter (the sticky app header uses `backdrop-blur-sm`)
 * becomes the containing block for `position: fixed` descendants, which would
 * otherwise anchor the overlay to that ancestor's box instead of the viewport.
 *
 * The panel uses `m-auto` inside a `min-h-full` flex row rather than
 * `items-center`: auto margins collapse to zero once free space goes negative,
 * so tall content top-aligns and stays scrollable instead of overflowing above
 * the viewport where it cannot be reached.
 */
export function Modal({
  open,
  onClose,
  label,
  labelledBy,
  className,
  rootClassName,
  overlayClassName,
  closeOnOverlayClick = true,
  children,
}: ModalProps) {
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  React.useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open || !mounted) return null;

  return createPortal(
    <div
      className={cn(
        "fixed inset-0 z-50 overflow-y-auto overscroll-contain",
        rootClassName,
      )}
      data-testid="modal-viewport"
    >
      <button
        type="button"
        className={cn(
          "fixed inset-0 bg-black/60 backdrop-blur-sm",
          overlayClassName,
        )}
        aria-label="Close"
        onClick={closeOnOverlayClick ? onClose : undefined}
      />
      <div className="relative flex min-h-full items-start justify-center p-4">
        <div
          role="dialog"
          aria-modal="true"
          aria-label={labelledBy ? undefined : label}
          aria-labelledby={labelledBy}
          className={cn("relative z-10 m-auto", className)}
        >
          {children}
        </div>
      </div>
    </div>,
    document.body,
  );
}

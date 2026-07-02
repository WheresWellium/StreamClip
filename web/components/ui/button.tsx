"use client";

import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils/format";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-sm text-sm font-medium ring-offset-background transition-[background-color,border-color,color,box-shadow,transform] duration-100 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-50 active:translate-x-px active:translate-y-px active:shadow-none",
  {
    variants: {
      variant: {
        default:
          "border border-sky-400 bg-primary text-primary-foreground shadow-[2px_2px_0_0_hsl(186_60%_3%/0.9)] hover:bg-sky-400",
        destructive:
          "border border-destructive bg-destructive text-destructive-foreground shadow-[2px_2px_0_0_hsl(186_60%_3%/0.9)] hover:bg-destructive/90",
        outline:
          "border border-frame/30 bg-transparent hover:border-frame/60 hover:bg-frame/5",
        secondary:
          "border border-frame/15 bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-frame/5 hover:text-foreground",
        link: "text-primary underline-offset-4 hover:underline active:translate-x-0 active:translate-y-0",
      },
      size: {
        default: "h-8 px-3.5",
        sm: "h-7 px-2.5 text-xs",
        lg: "h-9 px-6",
        icon: "h-8 w-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  /** Shown on hover/focus — explains what this button does. */
  tooltip?: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, tooltip, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    const button = (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );

    if (!tooltip) {
      return button;
    }

    return (
      <Tooltip>
        <TooltipTrigger asChild>{button}</TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs leading-relaxed">
          {tooltip}
        </TooltipContent>
      </Tooltip>
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };

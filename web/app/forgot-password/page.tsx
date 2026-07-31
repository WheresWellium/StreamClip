"use client";

import Link from "next/link";
import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import { forgotPasswordAction, type AuthActionState } from "@/lib/api/actions/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/form";
import { LabelWithTip } from "@/components/ui/help-tip";
import { AUTH_LEGEND } from "@/lib/help/legends";

const initial: AuthActionState = { status: "idle" };

function ForgotSubmitButton() {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" className="w-full" disabled={pending}>
      {pending ? "Sending…" : "Send reset link"}
    </Button>
  );
}

export default function ForgotPasswordPage() {
  const [state, formAction] = useActionState(forgotPasswordAction, initial);

  return (
    <div className="max-w-md mx-auto space-y-6 py-8">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-semibold">Forgot password</h1>
        <p className="text-sm text-muted-foreground">
          Enter your email and we&apos;ll send a reset link if an account exists.
        </p>
      </div>
      <form action={formAction} className="glossy-surface p-6 space-y-4">
        <LabelWithTip htmlFor="email" tip={AUTH_LEGEND.email} tipLabel="Email">
          Email
        </LabelWithTip>
        <Input id="email" name="email" type="email" required autoComplete="email" />
        {state.status === "error" && (
          <p className="text-xs text-destructive">{state.message}</p>
        )}
        {state.status === "ok" && (
          <p className="text-xs text-emerald-400">{state.message}</p>
        )}
        <ForgotSubmitButton />
      </form>
      <p className="text-center text-sm text-muted-foreground">
        <Link href="/login" className="text-sky-400 hover:underline">
          Back to sign in
        </Link>
      </p>
    </div>
  );
}

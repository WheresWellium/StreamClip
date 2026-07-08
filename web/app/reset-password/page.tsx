"use client";

import Link from "next/link";
import { Suspense, useActionState } from "react";
import { useSearchParams } from "next/navigation";

import { resetPasswordAction, type AuthActionState } from "@/lib/api/actions/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/form";
import { LabelWithTip } from "@/components/ui/help-tip";
import { AUTH_LEGEND } from "@/lib/help/legends";

const initial: AuthActionState = { status: "idle" };

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [state, formAction] = useActionState(resetPasswordAction, initial);

  if (!token) {
    return (
      <p className="text-sm text-destructive text-center">
        This reset link is invalid. Request a new one from{" "}
        <Link href="/forgot-password" className="text-sky-400 hover:underline">
          forgot password
        </Link>
        .
      </p>
    );
  }

  return (
    <form action={formAction} className="glossy-surface p-6 space-y-4">
      <input type="hidden" name="token" value={token} />
      <LabelWithTip htmlFor="password" tip={AUTH_LEGEND.password} tipLabel="Password">
        New password
      </LabelWithTip>
      <Input
        id="password"
        name="password"
        type="password"
        required
        minLength={8}
        autoComplete="new-password"
      />
      <LabelWithTip htmlFor="confirm_password" tip={AUTH_LEGEND.password} tipLabel="Confirm">
        Confirm password
      </LabelWithTip>
      <Input
        id="confirm_password"
        name="confirm_password"
        type="password"
        required
        minLength={8}
        autoComplete="new-password"
      />
      {state.status === "error" && (
        <p className="text-xs text-destructive">{state.message}</p>
      )}
      {state.status === "ok" && (
        <p className="text-xs text-emerald-400">{state.message}</p>
      )}
      <Button type="submit" className="w-full">
        Reset password
      </Button>
      {state.status === "ok" && (
        <p className="text-center text-sm">
          <Link href="/login" className="text-sky-400 hover:underline">
            Sign in →
          </Link>
        </p>
      )}
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="max-w-md mx-auto space-y-6 py-8">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-semibold">Reset password</h1>
        <p className="text-sm text-muted-foreground">Choose a new password for your account.</p>
      </div>
      <Suspense fallback={<p className="text-sm text-muted-foreground text-center">Loading…</p>}>
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}

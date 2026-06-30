"use client";

import { useFormState, useFormStatus } from "react-dom";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import {
  loginAction,
  logoutAction,
  registerAction,
  type AuthActionState,
} from "@/app/actions/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/form";
import { LabelWithTip } from "@/components/ui/help-tip";
import { SectionLegend } from "@/components/ui/section-legend";
import { AUTH_LEGEND } from "@/lib/help/legends";

const initial: AuthActionState = { status: "idle" };

function SubmitButton({ label }: { label: string }) {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" disabled={pending} className="w-full">
      {pending ? "…" : label}
    </Button>
  );
}

export function AuthPanel({ isAuthenticated = false }: { isAuthenticated?: boolean }) {
  const router = useRouter();
  const [loginState, loginFormAction] = useFormState(loginAction, initial);
  const [registerState, registerFormAction] = useFormState(registerAction, initial);

  useEffect(() => {
    if (loginState.status === "ok" || registerState.status === "ok") {
      router.refresh();
    }
  }, [loginState.status, registerState.status, router]);

  return (
    <div className="rounded-lg border border-border/60 bg-card p-4 space-y-4 max-w-md">
      <div className="flex items-center justify-between gap-2">
        <SectionLegend title="Account" tip={AUTH_LEGEND.privacy} className="normal-case tracking-normal" />
        {isAuthenticated && (
          <form action={logoutAction}>
            <Button type="submit" variant="ghost" size="sm">
              Sign out
            </Button>
          </form>
        )}
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        <form action={loginFormAction} className="space-y-2">
          <p className="text-sm font-medium">Sign in</p>
          <LabelWithTip htmlFor="login-email" tip={AUTH_LEGEND.email} tipLabel="Email help">
            Email
          </LabelWithTip>
          <Input id="login-email" name="email" type="email" placeholder="you@example.com" required />
          <LabelWithTip htmlFor="login-password" tip={AUTH_LEGEND.password} tipLabel="Password help">
            Password
          </LabelWithTip>
          <Input id="login-password" name="password" type="password" placeholder="Password" required />
          {loginState.status === "error" && (
            <p className="text-xs text-destructive">{loginState.message}</p>
          )}
          <SubmitButton label="Sign in" />
        </form>
        <form action={registerFormAction} className="space-y-2">
          <p className="text-sm font-medium">Register</p>
          <LabelWithTip htmlFor="reg-email" tip={AUTH_LEGEND.email} tipLabel="Email help">
            Email
          </LabelWithTip>
          <Input id="reg-email" name="email" type="email" placeholder="you@example.com" required />
          <LabelWithTip htmlFor="reg-password" tip={AUTH_LEGEND.password} tipLabel="Password help">
            Password
          </LabelWithTip>
          <Input id="reg-password" name="password" type="password" placeholder="Password (8+)" required minLength={8} />
          <LabelWithTip htmlFor="reg-display" tip={AUTH_LEGEND.displayName} tipLabel="Display name help">
            Display name
          </LabelWithTip>
          <Input id="reg-display" name="display_name" placeholder="Display name" />
          {registerState.status === "error" && (
            <p className="text-xs text-destructive">{registerState.message}</p>
          )}
          <SubmitButton label="Create account" />
        </form>
      </div>
    </div>
  );
}

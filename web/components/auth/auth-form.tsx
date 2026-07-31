"use client";

import Link from "next/link";
import { useFormStatus } from "react-dom";
import { useActionState, useEffect } from "react";
import { useRouter } from "next/navigation";

import type { AuthActionState } from "@/lib/api/actions/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/form";
import { LabelWithTip } from "@/components/ui/help-tip";
import { AUTH_LEGEND } from "@/lib/help/legends";
import { MIN_PASSWORD_LENGTH } from "@/lib/auth/password-policy";

const initial: AuthActionState = { status: "idle" };

function SubmitButton({ label }: { label: string }) {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" disabled={pending} className="w-full">
      {pending ? "…" : label}
    </Button>
  );
}

type Props = {
  mode: "login" | "register";
  action: (
    prev: AuthActionState,
    formData: FormData,
  ) => Promise<AuthActionState>;
};

export function AuthForm({ mode, action }: Props) {
  const router = useRouter();
  const [state, formAction] = useActionState(action, initial);

  useEffect(() => {
    if (state.status === "ok") router.push("/");
  }, [state.status, router]);

  return (
    <form action={formAction} className="glossy-surface p-6 space-y-4">
      <LabelWithTip htmlFor="email" tip={AUTH_LEGEND.email} tipLabel="Email">
        Email
      </LabelWithTip>
      <Input id="email" name="email" type="email" required autoComplete="email" />
      <LabelWithTip htmlFor="password" tip={AUTH_LEGEND.password} tipLabel="Password">
        Password
      </LabelWithTip>
      <Input
        id="password"
        name="password"
        type="password"
        required
        minLength={mode === "register" ? MIN_PASSWORD_LENGTH : undefined}
        autoComplete={mode === "login" ? "current-password" : "new-password"}
      />
      {mode === "register" && (
        <>
          <LabelWithTip htmlFor="confirm_password" tip={AUTH_LEGEND.password} tipLabel="Confirm password">
            Confirm password
          </LabelWithTip>
          <Input
            id="confirm_password"
            name="confirm_password"
            type="password"
            required
            minLength={MIN_PASSWORD_LENGTH}
            autoComplete="new-password"
          />
          <LabelWithTip htmlFor="display_name" tip={AUTH_LEGEND.displayName} tipLabel="Name">
            Display name
          </LabelWithTip>
          <Input id="display_name" name="display_name" />
        </>
      )}
      {mode === "login" && (
        <div className="flex items-center justify-between gap-2">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              name="remember_me"
              defaultChecked
              className="accent-sky-500"
            />
            Remember me
          </label>
          <Link href="/forgot-password" className="text-xs text-sky-400 hover:underline">
            Forgot password?
          </Link>
        </div>
      )}
      {state.status === "error" && (
        <p className="text-xs text-destructive">{state.message}</p>
      )}
      {state.status === "ok" && state.message && (
        <p className="text-xs text-emerald-400">{state.message}</p>
      )}
      <SubmitButton label={mode === "login" ? "Sign in" : "Create account"} />
    </form>
  );
}

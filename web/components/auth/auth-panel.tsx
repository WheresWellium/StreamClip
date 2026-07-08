"use client";

import { Loader2, LogOut } from "lucide-react";
import Link from "next/link";
import { useFormStatus } from "react-dom";
import { useRouter } from "next/navigation";
import { useActionState, useEffect, useState } from "react";

import {
  changePasswordAction,
  loginAction,
  logoutAction,
  registerAction,
  updateProfileAction,
  type AuthActionState,
} from "@/lib/api/actions/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/form";
import { LabelWithTip } from "@/components/ui/help-tip";
import { SectionLegend } from "@/components/ui/section-legend";
import { useToastSafe } from "@/components/providers/toast-provider";
import { AUTH_LEGEND } from "@/lib/help/legends";
import { getClientAccessToken } from "@/lib/auth/client-session";

const initial: AuthActionState = { status: "idle" };

type UserProfile = {
  email: string;
  display_name: string | null;
};

function SubmitButton({ label }: { label: string }) {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" disabled={pending} className="w-full">
      {pending ? "…" : label}
    </Button>
  );
}

function AuthPanelSignedIn() {
  const router = useRouter();
  const { push: toast } = useToastSafe();
  const token = getClientAccessToken();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [profilePending, setProfilePending] = useState(false);
  const [passwordPending, setPasswordPending] = useState(false);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/auth/me", {
          headers: { Authorization: `Bearer ${token}` },
          cache: "no-store",
        });
        if (!res.ok) return;
        const data = (await res.json()) as UserProfile;
        if (!cancelled) {
          setProfile(data);
          setDisplayName(data.display_name ?? "");
        }
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const handleLogout = async () => {
    await logoutAction();
    router.push("/");
    router.refresh();
  };

  const handleProfileSave = async () => {
    if (!token) return;
    setProfilePending(true);
    const result = await updateProfileAction(displayName, token);
    setProfilePending(false);
    if (result.status === "error") {
      toast("Could not save", result.message ?? "Try again.");
      return;
    }
    setProfile((prev) => (prev ? { ...prev, display_name: displayName } : prev));
    toast("Profile updated", "Your display name was saved.");
  };

  const handlePasswordChange = async () => {
    if (!token) return;
    if (newPassword !== confirmPassword) {
      toast("Passwords do not match", "Confirm your new password.");
      return;
    }
    setPasswordPending(true);
    const result = await changePasswordAction(currentPassword, newPassword, token);
    setPasswordPending(false);
    if (result.status === "error") {
      toast("Could not change password", result.message ?? "Try again.");
      return;
    }
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    toast("Password updated", "Use your new password next time you sign in.");
  };

  return (
    <div className="glossy-surface p-4 space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium">Signed in</p>
          <p className="text-xs text-muted-foreground">
            {profile?.email ?? "Loading account…"}
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={() => void handleLogout()}>
          <LogOut className="h-3.5 w-3.5" />
          Sign out
        </Button>
      </div>

      <div className="grid sm:grid-cols-2 gap-4 pt-2 border-t border-border/50">
        <div className="space-y-2">
          <p className="text-sm font-medium">Profile</p>
          <LabelWithTip htmlFor="profile-display" tip={AUTH_LEGEND.displayName} tipLabel="Display name">
            Display name
          </LabelWithTip>
          <Input
            id="profile-display"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Your name"
          />
          <Button
            type="button"
            size="sm"
            disabled={profilePending || !displayName.trim()}
            onClick={() => void handleProfileSave()}
          >
            {profilePending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Save profile"}
          </Button>
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium">Change password</p>
          <Input
            type="password"
            placeholder="Current password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            autoComplete="current-password"
          />
          <Input
            type="password"
            placeholder="New password (8+)"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            minLength={8}
            autoComplete="new-password"
          />
          <Input
            type="password"
            placeholder="Confirm new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            minLength={8}
            autoComplete="new-password"
          />
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={passwordPending || !currentPassword || newPassword.length < 8}
            onClick={() => void handlePasswordChange()}
          >
            {passwordPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Update password"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function AuthPanelSignedOut() {
  const router = useRouter();
  const [loginState, loginFormAction] = useActionState(loginAction, initial);
  const [registerState, registerFormAction] = useActionState(registerAction, initial);

  useEffect(() => {
    if (loginState.status === "ok" || registerState.status === "ok") {
      router.refresh();
    }
  }, [loginState.status, registerState.status, router]);

  return (
    <div className="glossy-surface p-4 space-y-4">
      <SectionLegend title="Account" tip={AUTH_LEGEND.privacy} className="normal-case tracking-normal" />
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
          <div className="flex items-center justify-between gap-2">
            <label className="flex items-center gap-2 text-xs cursor-pointer">
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
          <LabelWithTip htmlFor="reg-confirm" tip={AUTH_LEGEND.password} tipLabel="Confirm password">
            Confirm password
          </LabelWithTip>
          <Input id="reg-confirm" name="confirm_password" type="password" placeholder="Confirm password" required minLength={8} />
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

export function AuthPanel({ isAuthenticated = false }: { isAuthenticated?: boolean }) {
  if (isAuthenticated) {
    return <AuthPanelSignedIn />;
  }
  return <AuthPanelSignedOut />;
}

"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { registerAction } from "@/lib/api/actions/auth";
import { AuthForm } from "@/components/auth/auth-form";
import { getClientAccessToken } from "@/lib/auth/client-session";

export default function RegisterPage() {
  const router = useRouter();

  useEffect(() => {
    if (getClientAccessToken()) {
      router.replace("/");
    }
  }, [router]);

  return (
    <div className="max-w-md mx-auto space-y-6 py-8">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-semibold">Create account</h1>
        <p className="text-sm text-muted-foreground">
          Link device jobs and unlock saved templates.
        </p>
      </div>
      <AuthForm mode="register" action={registerAction} />
      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="text-sky-400 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}

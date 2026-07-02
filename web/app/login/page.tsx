import Link from "next/link";
import { redirect } from "next/navigation";

import { loginAction } from "@/app/actions/auth";
import { AuthForm } from "@/components/auth/auth-form";
import { getAccessToken } from "@/lib/auth/session";

export default async function LoginPage() {
  const token = await getAccessToken();
  if (token) redirect("/");

  return (
    <div className="max-w-md mx-auto space-y-6 py-8">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-semibold">Sign in</h1>
        <p className="text-sm text-muted-foreground">
          Access templates, webhooks, and cross-device job sync.
        </p>
      </div>
      <AuthForm mode="login" action={loginAction} />
      <p className="text-center text-sm text-muted-foreground">
        No account?{" "}
        <Link href="/register" className="text-sky-400 hover:underline">
          Register
        </Link>
      </p>
    </div>
  );
}

import Link from "next/link";
import { redirect } from "next/navigation";

import { registerAction } from "@/app/actions/auth";
import { AuthForm } from "@/components/auth/auth-form";
import { getAccessToken } from "@/lib/auth/session";

export default async function RegisterPage() {
  const token = await getAccessToken();
  if (token) redirect("/");

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

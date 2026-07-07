import { ApiClientError } from "@/lib/api/client";
import {
  clearAuthTokens,
  setAuthTokens,
} from "@/lib/auth/client-session";

export type AuthActionState = {
  status: "idle" | "ok" | "error";
  message?: string;
};

export async function loginAction(
  _prev: AuthActionState,
  formData: FormData,
): Promise<AuthActionState> {
  const email = formData.get("email")?.toString().trim() ?? "";
  const password = formData.get("password")?.toString() ?? "";

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      cache: "no-store",
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return {
        status: "error",
        message: body.message ?? "Login failed",
      };
    }
    const data = await res.json();
    setAuthTokens(data.access_token, data.refresh_token);
    return { status: "ok" };
  } catch (err) {
    return {
      status: "error",
      message: err instanceof Error ? err.message : "Login failed",
    };
  }
}

export async function registerAction(
  _prev: AuthActionState,
  formData: FormData,
): Promise<AuthActionState> {
  const email = formData.get("email")?.toString().trim() ?? "";
  const password = formData.get("password")?.toString() ?? "";
  const display_name = formData.get("display_name")?.toString().trim() || undefined;

  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, display_name }),
      cache: "no-store",
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return {
        status: "error",
        message: body.message ?? "Registration failed",
      };
    }
    const data = await res.json();
    setAuthTokens(data.access_token, data.refresh_token);
    return { status: "ok" };
  } catch (err) {
    return {
      status: "error",
      message: err instanceof Error ? err.message : "Registration failed",
    };
  }
}

export async function logoutAction(): Promise<void> {
  clearAuthTokens();
  if (typeof window !== "undefined") {
    window.location.href = "/";
  }
}

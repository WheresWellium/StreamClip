import {
  clearAuthTokens,
  setAuthTokens,
} from "@/lib/auth/client-session";

export type AuthActionState = {
  status: "idle" | "ok" | "error";
  message?: string;
};

function rememberMeFromForm(formData: FormData): boolean {
  return formData.get("remember_me") === "on";
}

export async function loginAction(
  _prev: AuthActionState,
  formData: FormData,
): Promise<AuthActionState> {
  const email = formData.get("email")?.toString().trim() ?? "";
  const password = formData.get("password")?.toString() ?? "";
  const remember_me = rememberMeFromForm(formData);

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, remember_me }),
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
    setAuthTokens(data.access_token, data.refresh_token, { rememberMe: remember_me });
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
  const confirmPassword = formData.get("confirm_password")?.toString() ?? "";
  const display_name = formData.get("display_name")?.toString().trim() || undefined;

  if (password !== confirmPassword) {
    return { status: "error", message: "Passwords do not match" };
  }

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
    setAuthTokens(data.access_token, data.refresh_token, { rememberMe: true });
    return { status: "ok" };
  } catch (err) {
    return {
      status: "error",
      message: err instanceof Error ? err.message : "Registration failed",
    };
  }
}

export async function forgotPasswordAction(
  _prev: AuthActionState,
  formData: FormData,
): Promise<AuthActionState> {
  const email = formData.get("email")?.toString().trim() ?? "";

  try {
    const res = await fetch("/api/auth/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
      cache: "no-store",
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return {
        status: "error",
        message: body.message ?? "Could not send reset email",
      };
    }
    return {
      status: "ok",
      message: "If an account exists for that email, a reset link has been sent.",
    };
  } catch (err) {
    return {
      status: "error",
      message: err instanceof Error ? err.message : "Could not send reset email",
    };
  }
}

export async function resetPasswordAction(
  _prev: AuthActionState,
  formData: FormData,
): Promise<AuthActionState> {
  const token = formData.get("token")?.toString() ?? "";
  const password = formData.get("password")?.toString() ?? "";
  const confirmPassword = formData.get("confirm_password")?.toString() ?? "";

  if (password !== confirmPassword) {
    return { status: "error", message: "Passwords do not match" };
  }

  try {
    const res = await fetch("/api/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: password }),
      cache: "no-store",
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return {
        status: "error",
        message: body.message ?? "Could not reset password",
      };
    }
    return { status: "ok", message: "Password updated. You can sign in now." };
  } catch (err) {
    return {
      status: "error",
      message: err instanceof Error ? err.message : "Could not reset password",
    };
  }
}

export async function logoutAction(): Promise<void> {
  clearAuthTokens();
  if (typeof window !== "undefined") {
    window.location.href = "/";
  }
}

export type ProfileActionState = {
  status: "idle" | "ok" | "error";
  message?: string;
};

export async function updateProfileAction(
  displayName: string,
  authToken: string,
): Promise<ProfileActionState> {
  try {
    const res = await fetch("/api/auth/me", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify({ display_name: displayName }),
      cache: "no-store",
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return {
        status: "error",
        message: body.message ?? "Could not update profile",
      };
    }
    return { status: "ok" };
  } catch (err) {
    return {
      status: "error",
      message: err instanceof Error ? err.message : "Could not update profile",
    };
  }
}

export async function changePasswordAction(
  currentPassword: string,
  newPassword: string,
  authToken: string,
): Promise<ProfileActionState> {
  if (newPassword.length < 8) {
    return { status: "error", message: "New password must be at least 8 characters" };
  }
  try {
    const res = await fetch("/api/auth/change-password", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
      cache: "no-store",
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return {
        status: "error",
        message: body.message ?? "Could not change password",
      };
    }
    return { status: "ok", message: "Password updated" };
  } catch (err) {
    return {
      status: "error",
      message: err instanceof Error ? err.message : "Could not change password",
    };
  }
}
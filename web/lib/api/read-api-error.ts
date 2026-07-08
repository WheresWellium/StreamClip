/** Parse FastAPI / BFF error bodies for user-visible messages. */

export function readApiErrorMessage(
  payload: unknown,
  fallback = "Request failed",
): string {
  if (!payload || typeof payload !== "object") return fallback;
  const body = payload as Record<string, unknown>;

  if (typeof body.message === "string" && body.message.trim()) {
    return body.message;
  }

  const detail = body.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (!item || typeof item !== "object") return "";
        const msg = (item as { msg?: unknown }).msg;
        return typeof msg === "string" ? msg : "";
      })
      .filter(Boolean);
    if (parts.length > 0) return parts.join("; ");
  }

  if (typeof body.code === "string" && body.code.trim()) {
    return body.code;
  }

  return fallback;
}

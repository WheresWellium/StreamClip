/** Parse FastAPI / BFF error bodies for user-visible messages. */

const INTERNAL_MESSAGE_RE =
  /traceback|file "|ytdlp|ffmpeg|\.py:|\\|[A-Z]:\\|Exception:|Error:/i;

export function isLikelyInternalErrorMessage(message: string): boolean {
  const text = message.trim();
  if (!text) return true;
  return text.length > 280 || INTERNAL_MESSAGE_RE.test(text);
}

export function readApiErrorMessage(
  payload: unknown,
  fallback = "Request failed",
): string {
  if (!payload || typeof payload !== "object") return fallback;
  const body = payload as Record<string, unknown>;

  if (typeof body.message === "string" && body.message.trim()) {
    const msg = body.message.trim();
    return isLikelyInternalErrorMessage(msg) ? fallback : msg;
  }

  const detail = body.detail;
  if (typeof detail === "string" && detail.trim()) {
    const msg = detail.trim();
    return isLikelyInternalErrorMessage(msg) ? fallback : msg;
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

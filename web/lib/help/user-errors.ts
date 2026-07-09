/** Client-side sanitization for error strings stored before B0 or from legacy rows. */

import { isLikelyInternalErrorMessage } from "@/lib/api/read-api-error";

const CODE_MESSAGES: Record<string, string> = {
  ingest_failed: "Could not download the source video.",
  invalid_source: "That URL or file isn't supported.",
  download_timeout: "The download took too long.",
  transcription_failed: "Couldn't transcribe the audio.",
  video_processing_failed: "Video processing failed.",
  ffmpeg_failed: "Video encoding failed.",
  quota_exceeded: "You've hit your processing quota.",
  audio_ingest_disabled: "Audio uploads require the audio-to-clip add-on.",
  WORKER_ERROR: "Publish failed. Try again or check your platform connection.",
  internal_error: "Something went wrong. Try again or report a bug.",
};

export function userFacingErrorMessage(
  message: string | null | undefined,
  code?: string | null,
  fallback = "Something went wrong.",
): string {
  if (code && CODE_MESSAGES[code]) {
    return CODE_MESSAGES[code];
  }
  if (!message || !message.trim()) {
    return fallback;
  }
  const text = message.trim();
  if (isLikelyInternalErrorMessage(text)) {
    return fallback;
  }
  return text;
}

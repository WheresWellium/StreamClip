/** Direct browser video uploads — presigned PUT to object storage. */
export const MAX_VIDEO_UPLOAD_BYTES = 5 * 1024 ** 3; // 5 GiB

export function formatMaxUploadLabel(): string {
  return "~5 GB";
}

export function validateVideoUploadSize(sizeBytes: number): string | null {
  if (sizeBytes <= 0) return "File is empty.";
  if (sizeBytes > MAX_VIDEO_UPLOAD_BYTES) {
    return `File exceeds ${formatMaxUploadLabel()} limit (${(sizeBytes / (1024 ** 3)).toFixed(1)} GB).`;
  }
  return null;
}

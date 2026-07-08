/**
 * Open a presigned clip URL for download without buffering the full file in RAM.
 * MinIO/S3 presigned URLs should include `response-content-disposition=attachment`.
 */
export async function downloadBlob(url: string, _filename: string): Promise<void> {
  window.open(url, "_blank", "noopener,noreferrer");
}

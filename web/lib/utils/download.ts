/**
 * Force-save a file by fetching it as a blob and triggering a programmatic
 * `<a download>` click. Works cross-origin (presigned MinIO / S3 URLs) where
 * the browser ignores the `download` attribute on a plain anchor tag.
 *
 * Falls back to `window.open` if the fetch fails (e.g. network error, CORS
 * misconfiguration) so the user can still access the file.
 *
 * Wire into clip-card.tsx once the P0 worker merges the URL-refresh fix (10.3).
 */
export async function downloadBlob(url: string, filename: string): Promise<void> {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = filename;
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(objectUrl);
  } catch {
    window.open(url, "_blank");
  }
}

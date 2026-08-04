/** Format the diagnostic line shown on the full-screen global error page. */
export function formatGlobalErrorDetail(error: {
  message?: string;
  digest?: string;
}): string {
  return [error.message, error.digest ? `ref ${error.digest}` : null]
    .filter(Boolean)
    .join(" · ");
}

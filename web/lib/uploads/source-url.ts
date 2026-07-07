/** Client-side source URL normalization before Zod validation. */

const SCHEMELESS_HOSTS = [
  /^twitch\.tv\//i,
  /^www\.twitch\.tv\//i,
  /^m\.twitch\.tv\//i,
  /^clips\.twitch\.tv\//i,
  /^kick\.com\//i,
  /^www\.kick\.com\//i,
  /^youtube\.com\//i,
  /^www\.youtube\.com\//i,
  /^youtu\.be\//i,
  /^tiktok\.com\//i,
  /^www\.tiktok\.com\//i,
  /^vm\.tiktok\.com\//i,
];

export function normalizeSourceUrl(raw: string | null | undefined): string | null {
  if (raw == null) return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  if (SCHEMELESS_HOSTS.some((re) => re.test(trimmed))) {
    return trimmed.toLowerCase().startsWith("www.")
      ? `https://${trimmed.slice(4)}`
      : `https://${trimmed}`;
  }
  return trimmed;
}

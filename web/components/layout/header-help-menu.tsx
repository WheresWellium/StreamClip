import Link from "next/link";

const DOCS_BASE = "https://streamclip-henna.vercel.app";

const HELP_LINKS = [
  { href: `${DOCS_BASE}/BETA_TESTER_QUICKSTART/`, label: "Quickstart" },
  { href: `${DOCS_BASE}/tutorials/TUTORIAL_INSTALL/`, label: "Install" },
  { href: `${DOCS_BASE}/tutorials/TUTORIAL_FIRST_JOB/`, label: "First job" },
  { href: `${DOCS_BASE}/tutorials/TUTORIAL_TROUBLESHOOTING/`, label: "Troubleshooting" },
  { href: `${DOCS_BASE}/BETA_KNOWN_ISSUES/`, label: "Known issues" },
] as const;

/** Docs help links for the header (MkDocs on Vercel). */
export function HeaderHelpMenu() {
  return (
    <div className="flex items-center gap-1 text-sm">
      <span className="text-muted-foreground hidden sm:inline px-1">Help</span>
      {HELP_LINKS.map(({ href, label }) => (
        <Link
          key={href}
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="px-2 py-1 rounded-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {label}
        </Link>
      ))}
    </div>
  );
}

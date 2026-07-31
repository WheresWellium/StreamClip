/**
 * Hierarchical parent for in-app Back when history is empty
 * (first open, deep link, Electron with no browser chrome).
 */
export function parentPath(pathname: string): string {
  const clean = (pathname || "/").replace(/\/+$/, "") || "/";
  if (clean === "/") return "/";

  // Treat distribution as a settings surface.
  if (clean === "/distribution") return "/settings";

  const segments = clean.split("/").filter(Boolean);
  if (segments.length <= 1) return "/";
  return `/${segments.slice(0, -1).join("/")}`;
}

export function canNavigateUp(pathname: string): boolean {
  const clean = (pathname || "/").replace(/\/+$/, "") || "/";
  return clean !== "/" && parentPath(clean) !== clean;
}

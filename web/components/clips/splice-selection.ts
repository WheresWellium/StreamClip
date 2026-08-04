/** Pure helpers for merge-toolbar clip selection (no React Set state). */

export function toggleSelectedId(selected: string[], id: string): string[] {
  return selected.includes(id)
    ? selected.filter((x) => x !== id)
    : [...selected, id];
}

export function pruneSelectedIds(
  selected: string[],
  eligibleIds: ReadonlySet<string> | readonly string[],
): string[] {
  const allow =
    eligibleIds instanceof Set ? eligibleIds : new Set(eligibleIds);
  return selected.filter((id) => allow.has(id));
}

export function setSelectedFromChecked(
  selected: string[],
  id: string,
  checked: boolean,
): string[] {
  if (checked) {
    return selected.includes(id) ? selected : [...selected, id];
  }
  return selected.filter((x) => x !== id);
}

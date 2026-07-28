/** Product default — keep in sync with `LicensingConfig.max_activations` (core/config). */
export const LICENSE_MAX_SEATS_HINT = 3;

/** Short, stable label for a machine id in the License seats list. */
export function formatDeviceLabel(machineId: string): string {
  const id = machineId.trim();
  if (id.length <= 16) return id;
  return `${id.slice(0, 8)}…${id.slice(-6)}`;
}

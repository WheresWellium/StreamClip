"use client";

import { useEffect, useState } from "react";

import {
  activateLicenseAction,
  getLicenseStatusAction,
  listLicenseSeatsAction,
  releaseLicenseSeatAction,
} from "@/lib/api/actions/license";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToastSafe } from "@/components/providers/toast-provider";
import type { LicenseActivation, LicenseActivationsResult, LicenseStatus } from "@/lib/api/client";
import { getLicenseMachineId } from "@/lib/license-machine-id";
import { formatDeviceLabel, LICENSE_MAX_SEATS_HINT } from "@/lib/license-seats";

function SeatUsageBar({ active, max }: { active: number; max: number }) {
  const capped = Math.min(active, max);
  const pct = max > 0 ? Math.round((capped / max) * 100) : 0;
  const atLimit = active >= max;
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="font-medium text-foreground">
          {active} of {max} seats in use
        </span>
        <span
          className={
            atLimit
              ? "text-xs text-amber-600 dark:text-amber-400"
              : "text-xs text-muted-foreground"
          }
        >
          {atLimit ? "At limit — release a seat to activate elsewhere" : `${max - active} free`}
        </span>
      </div>
      <div
        className="h-1.5 w-full overflow-hidden rounded-sm bg-frame/15"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={max}
        aria-valuenow={capped}
        aria-label="License seat usage"
      >
        <div
          className={
            atLimit
              ? "h-full bg-amber-500/90 transition-[width] duration-300"
              : "h-full bg-sky-400/90 transition-[width] duration-300"
          }
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function DeviceRow({
  device,
  busy,
  confirming,
  onAskRelease,
  onCancelConfirm,
  onConfirmRelease,
}: {
  device: LicenseActivation;
  busy: boolean;
  confirming: boolean;
  onAskRelease: () => void;
  onCancelConfirm: () => void;
  onConfirmRelease: () => void;
}) {
  return (
    <li className="flex flex-col gap-2 border-b border-border/40 py-3 last:border-0 last:pb-0 first:pt-0 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 space-y-0.5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-foreground">
            {formatDeviceLabel(device.machine_id)}
          </span>
          {device.is_current && (
            <span className="rounded-sm border border-sky-400/40 bg-sky-400/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-sky-600 dark:text-sky-300">
              This device
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground">
          Last seen {new Date(device.last_seen_at).toLocaleString()}
        </p>
      </div>
      {confirming ? (
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-xs text-muted-foreground sm:max-w-[14rem]">
            {device.is_current
              ? "Frees this install’s Pro unlock until you activate again."
              : "Frees this seat so another device can activate."}
          </p>
          <Button size="sm" variant="outline" disabled={busy} onClick={onCancelConfirm}>
            Cancel
          </Button>
          <Button
            size="sm"
            variant="destructive"
            disabled={busy}
            onClick={onConfirmRelease}
          >
            {busy ? "Releasing…" : "Confirm release"}
          </Button>
        </div>
      ) : (
        <Button
          size="sm"
          variant="outline"
          disabled={busy}
          onClick={onAskRelease}
          tooltip="Free this seat so another device can use your key (max 3)."
        >
          Release seat
        </Button>
      )}
    </li>
  );
}

export function LicensePanel() {
  const { push: toast } = useToastSafe();
  const [machineId] = useState(() => getLicenseMachineId());
  const [key, setKey] = useState("");
  /** Last key used for seat list/release (kept after activate clears the input). */
  const [seatKey, setSeatKey] = useState("");
  const [status, setStatus] = useState<LicenseStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showInstallId, setShowInstallId] = useState(false);

  const [seats, setSeats] = useState<LicenseActivationsResult | null>(null);
  const [seatsOpen, setSeatsOpen] = useState(false);
  const [seatsLoading, setSeatsLoading] = useState(false);
  const [seatsError, setSeatsError] = useState<string | null>(null);
  const [confirmMachineId, setConfirmMachineId] = useState<string | null>(null);
  const [releasingId, setReleasingId] = useState<string | null>(null);

  const activeSeatKey = () => {
    const fromInput = key.trim();
    if (fromInput.length >= 16) return fromInput;
    return seatKey.trim().length >= 16 ? seatKey.trim() : "";
  };

  const loadStatus = async () => {
    const result = await getLicenseStatusAction(machineId);
    if (result.status === "ok" && result.license) {
      setStatus(result.license);
    }
  };

  const loadSeats = async (licenseKey?: string) => {
    const trimmed = (licenseKey ?? activeSeatKey()).trim();
    if (trimmed.length < 16) {
      setSeatsError("Enter your full license key to manage device seats.");
      return null;
    }
    setSeatsLoading(true);
    setSeatsError(null);
    const result = await listLicenseSeatsAction(trimmed, machineId);
    setSeatsLoading(false);
    if (result.status === "error") {
      setSeats(null);
      setSeatsError(result.message ?? "Could not load device seats.");
      return null;
    }
    setSeatKey(trimmed);
    setSeats(result.seats ?? null);
    setSeatsOpen(true);
    return result.seats ?? null;
  };

  useEffect(() => {
    void loadStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activate = async () => {
    setLoading(true);
    setError(null);
    setSeatsError(null);
    const trimmed = key.trim();
    const result = await activateLicenseAction(trimmed, machineId);
    setLoading(false);
    if (result.status === "error") {
      setError(result.message ?? "Activation failed. Try again.");
      if (result.code === "activation_limit_reached") {
        setSeatKey(trimmed);
        setSeatsOpen(true);
        void loadSeats(trimmed);
      }
      return;
    }
    setStatus(result.license ?? null);
    setSeatKey(trimmed);
    setKey("");
    toast(
      "License activated",
      `${(result.license?.tier ?? "pro").toUpperCase()} tier is now active on this machine.`,
    );
    void loadStatus();
    void loadSeats(trimmed);
  };

  const releaseSeat = async (targetMachineId: string) => {
    const trimmed = activeSeatKey();
    if (trimmed.length < 16) {
      setSeatsError("Enter your license key before releasing a seat.");
      return;
    }
    setReleasingId(targetMachineId);
    setSeatsError(null);
    const result = await releaseLicenseSeatAction(trimmed, machineId, targetMachineId);
    setReleasingId(null);
    setConfirmMachineId(null);
    if (result.status === "error") {
      setSeatsError(result.message ?? "Could not release that device seat.");
      return;
    }
    const release = result.release;
    if (result.seats) {
      setSeats(result.seats);
      setSeatsOpen(true);
    }
    toast(
      "Seat released",
      release
        ? `${release.active_count} of ${release.max_activations} seats still in use.`
        : "That device can no longer use this key until reactivated.",
    );
    if (release?.current_device_released) {
      setStatus((prev) =>
        prev
          ? { ...prev, active: false, tier: "free", expires_at: null }
          : { active: false, tier: "free", expires_at: null, machine_id: machineId },
      );
      void loadStatus();
    }
  };

  const canManageSeats = activeSeatKey().length >= 16;

  return (
    <Card>
      <CardHeader>
        <CardTitle>License</CardTitle>
        <CardDescription>
          Pro unlocks higher clip counts and monthly quotas on this install.
          Keys work offline after first activation. Each key covers up to{" "}
          {LICENSE_MAX_SEATS_HINT} devices — release a seat when you switch machines.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            placeholder="SCPRO-XXXX-XXXX-XXXX-XXXX"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            disabled={loading}
            aria-label="License key"
          />
          <div className="flex gap-2 shrink-0">
            <Button onClick={() => void activate()} disabled={loading || !key.trim()}>
              {loading ? "Activating…" : "Activate"}
            </Button>
            <Button variant="outline" onClick={() => void loadStatus()} disabled={loading}>
              Refresh
            </Button>
          </div>
        </div>
        {error && (
          <p className="text-xs text-destructive" role="alert">
            {error}
          </p>
        )}

        {status && (
          <dl className="text-sm grid grid-cols-2 gap-2">
            <dt className="text-muted-foreground">Tier</dt>
            <dd className="uppercase">{status.tier}</dd>
            <dt className="text-muted-foreground">Active</dt>
            <dd>{status.active ? "Yes" : "No"}</dd>
            <dt className="text-muted-foreground">Expires</dt>
            <dd>{status.expires_at ?? "Never (perpetual)"}</dd>
            <dt className="text-muted-foreground">This install</dt>
            <dd>
              {showInstallId ? (
                <span className="font-mono text-xs truncate block">
                  {status.machine_id ?? machineId}
                </span>
              ) : (
                <button
                  type="button"
                  className="text-xs text-sky-400 hover:underline"
                  onClick={() => setShowInstallId(true)}
                >
                  Show details
                </button>
              )}
            </dd>
          </dl>
        )}

        <div className="space-y-3 border-t border-border/50 pt-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h4 className="text-sm font-medium text-foreground">Device seats</h4>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Paste your key, then load seats to free a device when you hit the{" "}
                {LICENSE_MAX_SEATS_HINT}-device limit.
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              disabled={!canManageSeats || seatsLoading || loading}
              onClick={() => void loadSeats()}
              tooltip="List devices using this key so you can free a seat."
            >
              {seatsLoading ? "Loading…" : seatsOpen && seats ? "Refresh seats" : "Manage seats"}
            </Button>
          </div>

          {seatsError && (
            <p className="text-xs text-destructive" role="alert">
              {seatsError}
            </p>
          )}

          {seatsOpen && seats && (
            <div className="space-y-3 rounded-sm border border-border/50 bg-frame/[0.03] p-3">
              <SeatUsageBar active={seats.active_count} max={seats.max_activations} />
              {seats.activations.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  No active devices on this key. Activate this install to claim a seat.
                </p>
              ) : (
                <ul className="m-0 list-none p-0">
                  {seats.activations.map((device) => (
                    <DeviceRow
                      key={device.machine_id}
                      device={device}
                      busy={releasingId === device.machine_id}
                      confirming={confirmMachineId === device.machine_id}
                      onAskRelease={() => setConfirmMachineId(device.machine_id)}
                      onCancelConfirm={() => setConfirmMachineId(null)}
                      onConfirmRelease={() => void releaseSeat(device.machine_id)}
                    />
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

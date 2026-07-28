/**
 * Loading lifecycle unit tests (tsx + node:test).
 * Run: npm run test:loading
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  INDETERMINATE_CAP,
  blendDeterminateProgress,
  computeLoadingLifecycle,
  indeterminateProgress,
} from "./lifecycle";
import { resolveLoadingConfig } from "./resolve-config";

describe("indeterminateProgress", () => {
  it("starts near zero and never reaches 100 alone", () => {
    assert.equal(indeterminateProgress(0, 90_000), 0);
    const mid = indeterminateProgress(30_000, 90_000);
    assert.ok(mid > 10 && mid < INDETERMINATE_CAP);
    const late = indeterminateProgress(90_000, 90_000);
    assert.ok(late <= INDETERMINATE_CAP);
    assert.ok(late < 100);
  });

  it("clamps negative and oversize elapsed", () => {
    assert.equal(indeterminateProgress(-100, 90_000), 0);
    assert.ok(indeterminateProgress(1_000_000, 90_000) <= INDETERMINATE_CAP);
  });
});

describe("blendDeterminateProgress", () => {
  it("does not snap backward below the soft floor", () => {
    const blended = blendDeterminateProgress(5, 40_000, 90_000);
    assert.ok(blended >= 5);
    assert.ok(blended < 100);
  });

  it("caps below 100 until completion", () => {
    assert.ok(blendDeterminateProgress(100, 1_000, 90_000) <= 99);
  });

  it("treats non-finite reported progress as soft floor", () => {
    const soft = blendDeterminateProgress(Number.NaN, 10_000, 90_000);
    assert.ok(soft > 0 && soft < INDETERMINATE_CAP);
  });
});

describe("computeLoadingLifecycle", () => {
  const base = {
    progress: 10,
    minDisplayMs: 900,
    exitMs: 480,
    maxWaitMs: 5_000,
    progressMode: "determinate" as const,
    exitRequested: false,
    exitElapsedMs: 0,
  };

  it("waits for min display before exit even when ready", () => {
    const early = computeLoadingLifecycle({
      ...base,
      isReady: true,
      nowMs: 200,
    });
    assert.equal(early.shouldStartExit, false);
    assert.equal(early.shouldUnmount, false);
    assert.ok(early.displayProgress < 100);
  });

  it("starts exit when ready and min display elapsed", () => {
    const ready = computeLoadingLifecycle({
      ...base,
      isReady: true,
      nowMs: 1_000,
    });
    assert.equal(ready.shouldStartExit, true);
    assert.equal(ready.displayProgress, 100);
  });

  it("force-completes on maxWait timeout", () => {
    const timed = computeLoadingLifecycle({
      ...base,
      isReady: false,
      nowMs: 5_000,
    });
    assert.equal(timed.timedOut, true);
    assert.equal(timed.shouldStartExit, true);
  });

  it("unmounts only after exit duration", () => {
    const exiting = computeLoadingLifecycle({
      ...base,
      isReady: true,
      nowMs: 2_000,
      exitRequested: true,
      exitElapsedMs: 100,
    });
    assert.equal(exiting.phase, "exiting");
    assert.equal(exiting.shouldUnmount, false);

    const done = computeLoadingLifecycle({
      ...base,
      isReady: true,
      nowMs: 2_000,
      exitRequested: true,
      exitElapsedMs: 500,
    });
    assert.equal(done.phase, "done");
    assert.equal(done.shouldUnmount, true);
  });

  it("maps boot → entering → loading phases", () => {
    const boot = computeLoadingLifecycle({
      ...base,
      isReady: false,
      nowMs: 40,
    });
    assert.equal(boot.phase, "boot");

    const entering = computeLoadingLifecycle({
      ...base,
      isReady: false,
      nowMs: 200,
    });
    assert.equal(entering.phase, "entering");

    const loading = computeLoadingLifecycle({
      ...base,
      isReady: false,
      nowMs: 500,
    });
    assert.equal(loading.phase, "loading");
  });

  it("uses indeterminate curve when mode is indeterminate", () => {
    const snap = computeLoadingLifecycle({
      ...base,
      isReady: false,
      progressMode: "indeterminate",
      progress: 80,
      nowMs: 400,
    });
    assert.ok(snap.displayProgress < 40);
    assert.equal(snap.shouldStartExit, false);
  });

  it("snaps progress to 100 once exit is requested", () => {
    const snap = computeLoadingLifecycle({
      ...base,
      isReady: true,
      nowMs: 2_000,
      exitRequested: true,
      exitElapsedMs: 50,
      progress: 12,
    });
    assert.equal(snap.displayProgress, 100);
    assert.equal(snap.phase, "exiting");
  });
});

describe("resolveLoadingConfig", () => {
  it("applies qClip defaults for empty config", () => {
    const cfg = resolveLoadingConfig({});
    assert.equal(cfg.title, "qClip");
    assert.equal(cfg.coverSrc, "/loading/cover.svg");
    assert.equal(cfg.animationVariant, "cinematic");
    assert.ok(cfg.minDisplayMs > 0);
    assert.ok(cfg.maxWaitMs >= 1_000);
  });

  it("allows cover and theme overrides", () => {
    const cfg = resolveLoadingConfig({
      title: "Custom",
      coverSrc: "/loading/alt.svg",
      accentColor: "#fff",
      animationVariant: "terminal",
      overlayOpacity: 2,
    });
    assert.equal(cfg.title, "Custom");
    assert.equal(cfg.coverSrc, "/loading/alt.svg");
    assert.equal(cfg.animationVariant, "terminal");
    assert.equal(cfg.overlayOpacity, 1);
  });

  it("falls back on invalid enums and empty strings", () => {
    const cfg = resolveLoadingConfig({
      title: "   ",
      coverSrc: "  ",
      animationVariant: "neon" as never,
      progressMode: "maybe" as never,
      reducedMotion: "nope" as never,
      tips: ["", "  keep me  ", ""],
      tipIntervalMs: 100,
      maxWaitMs: 50,
    });
    assert.equal(cfg.title, "qClip");
    assert.equal(cfg.coverSrc, undefined);
    assert.equal(cfg.animationVariant, "cinematic");
    assert.equal(cfg.progressMode, "indeterminate");
    assert.equal(cfg.reducedMotion, "respect");
    assert.deepEqual(cfg.tips, ["  keep me  "]);
    assert.equal(cfg.tipIntervalMs, 800);
    assert.equal(cfg.maxWaitMs, 1_000);
  });

  it("clamps progress and focal point", () => {
    const cfg = resolveLoadingConfig({
      progress: 140,
      coverFocalPoint: { x: -10, y: 200 },
    });
    assert.equal(cfg.progress, 100);
    assert.equal(cfg.coverFocalPoint.x, 0);
    assert.equal(cfg.coverFocalPoint.y, 100);
  });
});

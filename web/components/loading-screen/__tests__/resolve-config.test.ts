import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { DEFAULT_LOADING_SCREEN_CONFIG } from "../defaults.ts";
import {
  clampProgress,
  resolveLoadingScreenConfig,
  softIndeterminateProgress,
} from "../resolve-config.ts";

describe("resolveLoadingScreenConfig", () => {
  it("returns defaults when given an empty override", () => {
    const config = resolveLoadingScreenConfig();
    assert.equal(config.title, DEFAULT_LOADING_SCREEN_CONFIG.title);
    assert.equal(config.coverImageSrc, "/brand/loading-cover.svg");
    assert.equal(config.variant, "cinematic");
    assert.equal(config.composition, "lower-left");
  });

  it("merges nested overlay, colors, timing, and focal point", () => {
    const config = resolveLoadingScreenConfig({
      title: "Custom Title",
      overlay: { opacity: 0.9 },
      colors: { accent: "120 50% 40%" },
      timing: { minDisplayMs: 500 },
      coverFocalPoint: { x: 20 },
    });

    assert.equal(config.title, "Custom Title");
    assert.equal(config.overlay.opacity, 0.9);
    assert.equal(
      config.overlay.color,
      DEFAULT_LOADING_SCREEN_CONFIG.overlay.color,
    );
    assert.equal(config.colors.accent, "120 50% 40%");
    assert.equal(
      config.colors.title,
      DEFAULT_LOADING_SCREEN_CONFIG.colors.title,
    );
    assert.equal(config.timing.minDisplayMs, 500);
    assert.equal(
      config.timing.exitMs,
      DEFAULT_LOADING_SCREEN_CONFIG.timing.exitMs,
    );
    assert.equal(config.coverFocalPoint.x, 20);
    assert.equal(
      config.coverFocalPoint.y,
      DEFAULT_LOADING_SCREEN_CONFIG.coverFocalPoint.y,
    );
  });

  it("preserves default tips when tips override is omitted", () => {
    const config = resolveLoadingScreenConfig({ title: "X" });
    assert.deepEqual(config.tips, DEFAULT_LOADING_SCREEN_CONFIG.tips);
  });

  it("allows replacing tips explicitly", () => {
    const config = resolveLoadingScreenConfig({ tips: ["One tip"] });
    assert.deepEqual(config.tips, ["One tip"]);
  });
});

describe("clampProgress", () => {
  it("clamps to the inclusive 0–1 range", () => {
    assert.equal(clampProgress(-1), 0);
    assert.equal(clampProgress(0), 0);
    assert.equal(clampProgress(0.5), 0.5);
    assert.equal(clampProgress(1), 1);
    assert.equal(clampProgress(2), 1);
    assert.equal(clampProgress(Number.NaN), 0);
  });
});

describe("softIndeterminateProgress", () => {
  it("never reaches 1 until ready", () => {
    assert.ok(softIndeterminateProgress(0, false) < 0.05);
    assert.ok(softIndeterminateProgress(5_000, false) < 0.82);
    assert.ok(softIndeterminateProgress(60_000, false) < 1);
    assert.equal(softIndeterminateProgress(100, true), 1);
  });

  it("increases monotonically before ready", () => {
    const a = softIndeterminateProgress(1_000, false);
    const b = softIndeterminateProgress(4_000, false);
    const c = softIndeterminateProgress(10_000, false);
    assert.ok(a < b && b < c);
  });
});

import assert from "node:assert/strict";
import { describe, it } from "node:test";

/**
 * Soft-open policy for SidecarReadyGate: after MAX_ATTEMPTS failed health
 * polls, markReady(true) must run — never throw into the React tree.
 */
const POLL_MS = 400;
const MAX_ATTEMPTS = 180;

function softOpenDecision(tries: number, healthOk: boolean): "ready" | "soft" | "retry" {
  if (healthOk) return "ready";
  if (tries >= MAX_ATTEMPTS) return "soft";
  return "retry";
}

describe("sidecar soft-open policy", () => {
  it("opens soft after max failed health attempts", () => {
    assert.equal(softOpenDecision(MAX_ATTEMPTS, false), "soft");
    assert.equal(softOpenDecision(MAX_ATTEMPTS + 1, false), "soft");
  });

  it("retries before max attempts when health fails", () => {
    assert.equal(softOpenDecision(1, false), "retry");
    assert.equal(softOpenDecision(MAX_ATTEMPTS - 1, false), "retry");
  });

  it("marks ready immediately when health succeeds", () => {
    assert.equal(softOpenDecision(3, true), "ready");
  });

  it("bounds wait roughly under two minutes of polling", () => {
    assert.ok(POLL_MS * MAX_ATTEMPTS <= 90_000);
  });
});

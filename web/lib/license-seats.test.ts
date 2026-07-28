/**
 * License seat helpers.
 * Run: npm run test:license-seats
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { formatDeviceLabel, LICENSE_MAX_SEATS_HINT } from "./license-seats";

describe("LICENSE_MAX_SEATS_HINT", () => {
  it("matches the product default of 3 seats", () => {
    assert.equal(LICENSE_MAX_SEATS_HINT, 3);
  });
});

describe("formatDeviceLabel", () => {
  it("keeps short ids intact", () => {
    assert.equal(formatDeviceLabel("machine-1"), "machine-1");
  });

  it("truncates long ids with an ellipsis bridge", () => {
    const label = formatDeviceLabel("abcdefghijklmnopqrstuvwxyz012345");
    assert.ok(label.includes("…"));
    assert.ok(label.startsWith("abcdefgh"));
    assert.ok(label.endsWith("012345"));
  });
});

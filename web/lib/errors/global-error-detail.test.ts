import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { formatGlobalErrorDetail } from "./global-error-detail";

describe("formatGlobalErrorDetail", () => {
  it("joins message and digest for the crash page", () => {
    assert.equal(
      formatGlobalErrorDetail({
        message: "Cannot read properties of undefined",
        digest: "abc123",
      }),
      "Cannot read properties of undefined · ref abc123",
    );
  });

  it("omits missing pieces", () => {
    assert.equal(formatGlobalErrorDetail({ message: "boom" }), "boom");
    assert.equal(formatGlobalErrorDetail({ digest: "xyz" }), "ref xyz");
    assert.equal(formatGlobalErrorDetail({}), "");
  });
});

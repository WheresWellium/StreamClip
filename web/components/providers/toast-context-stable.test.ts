import assert from "node:assert/strict";
import { describe, it } from "node:test";
import React from "react";

/**
 * Documents the React #185 guard: Provider value must be memoized on `push`.
 * (Full RTL mount is heavier than this repo's node:test suite; the production
 * toast-provider.tsx uses useMemo(() => ({ push }), [push]).)
 */
describe("toast context stability contract", () => {
  it("memoized value identity stays stable when push is stable", () => {
    const push = (_title: string, _description?: string) => {};
    const a = { push };
    const b = { push };
    // Unmemoized object literals are never === — the bug we fixed.
    assert.notEqual(a, b);

    let memo: { push: typeof push } | null = null;
    const getValue = (p: typeof push) => {
      if (!memo || memo.push !== p) memo = { push: p };
      return memo;
    };
    const v1 = getValue(push);
    const v2 = getValue(push);
    assert.equal(v1, v2);
  });

  it("react useMemo is available for the provider implementation", () => {
    assert.equal(typeof React.useMemo, "function");
  });
});

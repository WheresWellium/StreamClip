import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  pruneSelectedIds,
  setSelectedFromChecked,
  toggleSelectedId,
} from "./splice-selection";

describe("splice-selection", () => {
  it("toggles ids without Set state", () => {
    assert.deepEqual(toggleSelectedId([], "a"), ["a"]);
    assert.deepEqual(toggleSelectedId(["a"], "b"), ["a", "b"]);
    assert.deepEqual(toggleSelectedId(["a", "b"], "a"), ["b"]);
  });

  it("setSelectedFromChecked mirrors checkbox event", () => {
    assert.deepEqual(setSelectedFromChecked([], "a", true), ["a"]);
    assert.deepEqual(setSelectedFromChecked(["a"], "a", true), ["a"]);
    assert.deepEqual(setSelectedFromChecked(["a", "b"], "a", false), ["b"]);
    assert.equal(setSelectedFromChecked(["a", "b"], "a", true).length, 2);
  });

  it("prunes ids that leave eligible set", () => {
    assert.deepEqual(pruneSelectedIds(["a", "b", "c"], ["a", "c"]), ["a", "c"]);
    assert.deepEqual(pruneSelectedIds(["a", "b"], new Set(["b"])), ["b"]);
  });

  it("two selections yield count 2 for merge gate", () => {
    let selected: string[] = [];
    selected = setSelectedFromChecked(selected, "clip-1", true);
    selected = setSelectedFromChecked(selected, "clip-3", true);
    assert.equal(selected.length, 2);
    assert.ok(selected.includes("clip-1"));
    assert.ok(selected.includes("clip-3"));
  });
});

/**
 * Run: npx --yes tsx --test lib/navigation/parent-path.test.ts
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { canNavigateUp, parentPath } from "./parent-path";

describe("parentPath", () => {
  it("keeps home at home", () => {
    assert.equal(parentPath("/"), "/");
    assert.equal(parentPath(""), "/");
  });

  it("lifts top-level sections to home", () => {
    assert.equal(parentPath("/jobs"), "/");
    assert.equal(parentPath("/vault"), "/");
    assert.equal(parentPath("/settings"), "/");
    assert.equal(parentPath("/help"), "/");
    assert.equal(parentPath("/login"), "/");
  });

  it("walks nested job and settings routes", () => {
    assert.equal(parentPath("/jobs/new"), "/jobs");
    assert.equal(parentPath("/jobs/abc"), "/jobs");
    assert.equal(parentPath("/jobs/abc/clips"), "/jobs/abc");
    assert.equal(parentPath("/settings/assets"), "/settings");
    assert.equal(parentPath("/settings/templates"), "/settings");
  });

  it("maps distribution under settings", () => {
    assert.equal(parentPath("/distribution"), "/settings");
  });

  it("strips trailing slashes", () => {
    assert.equal(parentPath("/jobs/"), "/");
    assert.equal(parentPath("/jobs/new/"), "/jobs");
  });
});

describe("canNavigateUp", () => {
  it("is false only on home", () => {
    assert.equal(canNavigateUp("/"), false);
    assert.equal(canNavigateUp("/jobs"), true);
    assert.equal(canNavigateUp("/jobs/new"), true);
  });
});

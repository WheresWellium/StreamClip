/**
 * Run: npx --yes tsx --test lib/jobs/job-route-id.test.ts
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  afterCreateJobSuccess,
  isPlaceholderJobPath,
  parseJobIdFromPathname,
  resolveJobId,
  jobClipsPath,
  jobOverviewPath,
  navigateToJob,
} from "./job-route-id";

describe("parseJobIdFromPathname", () => {
  it("reads real job ids from overview and clips paths", () => {
    assert.equal(parseJobIdFromPathname("/jobs/abc-123/"), "abc-123");
    assert.equal(parseJobIdFromPathname("/jobs/abc-123"), "abc-123");
    assert.equal(parseJobIdFromPathname("/jobs/abc-123/clips/"), "abc-123");
  });

  it("rejects placeholder, new, and non-job paths", () => {
    assert.equal(parseJobIdFromPathname("/jobs/_/"), null);
    assert.equal(parseJobIdFromPathname("/jobs/_/clips/"), null);
    assert.equal(parseJobIdFromPathname("/jobs/new"), null);
    assert.equal(parseJobIdFromPathname("/jobs"), null);
    assert.equal(parseJobIdFromPathname("/vault"), null);
  });
});

describe("resolveJobId", () => {
  it("prefers pathname over baked static placeholder param", () => {
    assert.equal(resolveJobId("_", "/jobs/real-id/"), "real-id");
    assert.equal(resolveJobId("real-id", "/jobs/real-id/clips/"), "real-id");
  });

  it("returns null when only the static placeholder is available", () => {
    assert.equal(resolveJobId("_", "/jobs/_/"), null);
    assert.equal(resolveJobId(undefined, "/jobs/new/"), null);
  });

  it("falls back to a concrete param when path has no id", () => {
    assert.equal(resolveJobId("from-param", "/jobs"), "from-param");
  });
});

describe("helpers", () => {
  it("builds job hrefs for hard navigation", () => {
    assert.equal(jobOverviewPath("x"), "/jobs/x/");
    assert.equal(jobClipsPath("x"), "/jobs/x/clips/");
  });

  it("detects placeholder shells", () => {
    assert.equal(isPlaceholderJobPath("/jobs/_/"), true);
    assert.equal(isPlaceholderJobPath("/jobs/abc/"), false);
  });
});

describe("afterCreateJobSuccess", () => {
  it("navigates immediately even when onJobCreated rejects", async () => {
    const assigned: string[] = [];
    // @ts-expect-error node stub
    globalThis.window = {
      location: { assign: (url: string) => assigned.push(url) },
      sessionStorage: { setItem() {}, getItem() { return null; } },
    };
    try {
      afterCreateJobSuccess("abc", async () => {
        throw new Error("caller boom");
      });
      assert.deepEqual(assigned, ["/jobs/abc/"]);
      // Let the rejected promise settle without failing the test runner.
      await new Promise((r) => setImmediate(r));
    } finally {
      // @ts-expect-error teardown
      delete globalThis.window;
    }
  });

  it("navigateToJob uses trailing-slash overview path", () => {
    const assigned: string[] = [];
    // @ts-expect-error node stub
    globalThis.window = {
      location: { assign: (url: string) => assigned.push(url) },
      sessionStorage: { setItem() {}, getItem() { return null; } },
    };
    try {
      navigateToJob("z");
      assert.deepEqual(assigned, ["/jobs/z/"]);
    } finally {
      // @ts-expect-error teardown
      delete globalThis.window;
    }
  });
});

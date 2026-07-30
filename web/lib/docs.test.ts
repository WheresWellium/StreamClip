/**
 * Help / henna docs path helpers.
 * Run: npm run test:docs
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  HELP_TOPICS,
  LEGACY_HELP_DOCS_PATHS,
  clampHelpDocsPathForProduct,
  helpHref,
  isPublicHelpDocsPath,
  remapLegacyHelpDocsPath,
  resolveHelpDocsPath,
} from "./docs";

describe("helpHref", () => {
  it("returns bare /help for home", () => {
    assert.equal(helpHref("/"), "/help");
    assert.equal(helpHref(""), "/help");
  });

  it("encodes section anchors for the in-app viewer", () => {
    assert.equal(
      helpHref("/#download"),
      "/help?path=%2F%23download",
    );
  });
});

describe("remapLegacyHelpDocsPath", () => {
  it("maps retired pages to home or section anchors", () => {
    assert.equal(
      remapLegacyHelpDocsPath("/tutorials/TUTORIAL_INSTALL"),
      "/#download",
    );
    assert.equal(
      remapLegacyHelpDocsPath("/tutorials/TUTORIAL_FIRST_JOB/"),
      "/#use",
    );
    assert.equal(
      remapLegacyHelpDocsPath("/MACOS_INSTALLER"),
      "/#download",
    );
    assert.equal(remapLegacyHelpDocsPath("/BETA_FAQ/"), "/");
    assert.equal(
      remapLegacyHelpDocsPath("/tutorials/TUTORIAL_TROUBLESHOOTING/"),
      "/",
    );
  });

  it("leaves published topic paths unchanged", () => {
    for (const topic of HELP_TOPICS) {
      assert.equal(remapLegacyHelpDocsPath(topic.docsPath), topic.docsPath);
    }
  });

  it("covers every vercel-style legacy redirect key", () => {
    assert.ok(Object.keys(LEGACY_HELP_DOCS_PATHS).length >= 8);
  });
});

describe("isPublicHelpDocsPath", () => {
  it("allows docs home and section anchors only", () => {
    assert.equal(isPublicHelpDocsPath("/"), true);
    assert.equal(isPublicHelpDocsPath("/#download"), true);
    assert.equal(isPublicHelpDocsPath("/#use"), true);
    assert.equal(isPublicHelpDocsPath("/BETA_FAQ/"), false);
    assert.equal(isPublicHelpDocsPath("/GAP_ANALYSIS/"), false);
  });
});

describe("clampHelpDocsPathForProduct", () => {
  it("remaps legacy then allows the published target", () => {
    assert.equal(
      clampHelpDocsPathForProduct("/tutorials/TUTORIAL_GPU_SETUP/", false),
      "/",
    );
    assert.equal(
      clampHelpDocsPathForProduct("/BETA_DOWNLOAD/", false),
      "/#download",
    );
  });

  it("clamps unknown operator paths to home when locked down", () => {
    assert.equal(
      clampHelpDocsPathForProduct("/PERFORMANCE/", false),
      "/",
    );
  });

  it("keeps remapped legacy even when operator paths are allowed", () => {
    assert.equal(
      clampHelpDocsPathForProduct("/BETA_TESTER_PLAN/", true),
      "/#use",
    );
  });
});

describe("resolveHelpDocsPath", () => {
  it("defaults empty input to docs home", () => {
    assert.equal(resolveHelpDocsPath(null), "/");
    assert.equal(resolveHelpDocsPath("  "), "/");
  });

  it("rejects foreign absolute URLs", () => {
    assert.equal(resolveHelpDocsPath("https://example.com/docs/"), "/");
  });

  it("preserves section anchors on home", () => {
    assert.equal(resolveHelpDocsPath("/#download"), "/#download");
    assert.equal(resolveHelpDocsPath("/#use"), "/#use");
  });

  it("remaps legacy paths before clamping", () => {
    assert.equal(
      resolveHelpDocsPath("/tutorials/TUTORIAL_INSTALL/"),
      "/#download",
    );
  });
});

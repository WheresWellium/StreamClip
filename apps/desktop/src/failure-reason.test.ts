import assert from "node:assert/strict";
import { test } from "node:test";

import {
  extractFatalFromLog,
  failureReasonFor,
  shouldShowErrorPage,
} from "./failure-reason";

test("spawn error takes precedence and is surfaced verbatim (F4)", () => {
  assert.equal(
    failureReasonFor("Sidecar executable missing: C:/x/streamclip-sidecar.exe", null),
    "Sidecar executable missing: C:/x/streamclip-sidecar.exe",
  );
});

test("FATAL log line is preferred over bare exit code (F1/F4)", () => {
  assert.equal(
    failureReasonFor(
      null,
      { code: 1, signal: null },
      "FATAL: qClip cannot write to its data folders. Unwritable: output",
    ),
    "qClip cannot write to its data folders. Unwritable: output",
  );
});

test("non-zero exit yields a legible reason with the code (F4)", () => {
  assert.equal(
    failureReasonFor(null, { code: 1, signal: null }),
    "Local engine exited (code 1) before it finished starting. Open the engine log for details.",
  );
});

test("unknown exit code still yields a message, never blank (F4)", () => {
  assert.equal(
    failureReasonFor(null, { code: null, signal: "SIGKILL" }),
    "Local engine exited (code unknown) before it finished starting. Open the engine log for details.",
  );
});

test("timeout with no crash evidence still yields a message", () => {
  assert.equal(failureReasonFor(null, null), "Local engine did not respond in time.");
});

test("failure reason is never empty for any observed failure state", () => {
  for (const spawnError of [null, "boom"]) {
    for (const exit of [null, { code: 0, signal: null }, { code: 137, signal: null }]) {
      const reason = failureReasonFor(spawnError, exit);
      assert.ok(reason.length > 0, "reason must never be blank");
    }
  }
});

test("shouldShowErrorPage triggers only when the process is dead with evidence", () => {
  assert.equal(shouldShowErrorPage(true, "boom", { code: 1, signal: null }), false);
  assert.equal(shouldShowErrorPage(false, "boom", null), true);
  assert.equal(shouldShowErrorPage(false, null, { code: 1, signal: null }), true);
  assert.equal(shouldShowErrorPage(false, null, null), false);
});

test("extractFatalFromLog returns the last FATAL line", () => {
  const log = [
    "info start",
    "FATAL: first problem",
    "more noise",
    "FATAL: qClip cannot write to its data folders. Unwritable: license_file",
  ].join("\n");
  assert.equal(
    extractFatalFromLog(log),
    "FATAL: qClip cannot write to its data folders. Unwritable: license_file",
  );
  assert.equal(extractFatalFromLog("no fatals here"), null);
});

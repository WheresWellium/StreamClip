import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  rewriteLegacyTwitchError,
  userFacingErrorMessage,
} from "./user-errors";

describe("userFacingErrorMessage Twitch/SSE rewrites", () => {
  it("rewrites Twitch 202 live-stream jargon on clip cards", () => {
    const raw =
      "202: live stream unavailable, use a permanent link instead.";
    assert.match(rewriteLegacyTwitchError(raw), /downloadable VOD/i);
    assert.match(userFacingErrorMessage(raw), /downloadable VOD/i);
  });

  it("rewrites SSE polling banner if it leaked into an error field", () => {
    const raw = "Live stream unavailable — refreshing via API";
    assert.match(userFacingErrorMessage(raw), /Progress updates were interrupted/i);
  });
});

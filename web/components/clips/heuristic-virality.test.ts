import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  isHeuristicVirality,
  shouldShowHeuristicViralityBanner,
} from "./heuristic-virality";

type Clip = Parameters<typeof isHeuristicVirality>[0];

function clip(overrides: Partial<Clip> = {}): Clip {
  return {
    id: "c1",
    rank: 0,
    title: "t",
    hook: "",
    emotion: "hype",
    start_secs: 0,
    end_secs: 10,
    duration_secs: 10,
    ensemble_score: 0,
    llm_score: 0,
    audio_score: 0,
    spectral_score: 0,
    flow_score: 0,
    chat_score: 0,
    status: "done",
    error_message: null,
    render_time_secs: 0,
    file_size_bytes: 0,
    transcript_text: "",
    llm_reason: "",
    meme_keywords: [],
    overlays: [],
    kind: "discovery",
    parent_clip_ids: [],
    render_overrides: {},
    approval_status: "draft",
    download_url: null,
    thumbnail_url: null,
    publish_statuses: [],
    ...overrides,
  } as Clip;
}

describe("heuristic virality banner gate", () => {
  it("detects virality_source=heuristic and Heuristic reason prefix", () => {
    assert.equal(isHeuristicVirality(clip({ virality_source: "heuristic" })), true);
    assert.equal(
      isHeuristicVirality(clip({ llm_reason: "Heuristic audio+novelty blend" })),
      true,
    );
    assert.equal(isHeuristicVirality(clip({ virality_source: "llm" })), false);
  });

  it("shows banner when majority of clips are heuristic", () => {
    assert.equal(shouldShowHeuristicViralityBanner([]), false);
    assert.equal(
      shouldShowHeuristicViralityBanner([
        clip({ id: "a", virality_source: "heuristic" }),
        clip({ id: "b", virality_source: "llm" }),
      ]),
      true,
    );
    assert.equal(
      shouldShowHeuristicViralityBanner([
        clip({ id: "a", virality_source: "llm" }),
        clip({ id: "b", virality_source: "llm" }),
        clip({ id: "c", virality_source: "heuristic" }),
      ]),
      false,
    );
  });
});

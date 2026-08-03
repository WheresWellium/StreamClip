/**
 * Create → live-job navigation matrix.
 * Run: npm run test:create-nav-matrix
 *
 * 9 profiles × 5 aspects × {1,5,10,20} clips → createJobAction ok + `/jobs/{id}/`.
 */
import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";

import { createJobAction } from "@/lib/api/actions/jobs";
import {
  ASPECT_RATIO_IDS,
  CONTENT_PROFILE_IDS,
} from "@/lib/creator-option-ids";
import { afterCreateJobSuccess, jobOverviewPath } from "@/lib/jobs/job-route-id";

const CLIP_COUNTS = [1, 5, 10, 20] as const;

const EXPECTED_PROFILES = [
  "gaming",
  "esports",
  "irl",
  "vlog",
  "podcast",
  "education",
  "sports",
  "music",
  "general",
] as const;

const EXPECTED_ASPECTS = ["9:16", "1:1", "4:5", "16:9", "2:3"] as const;

function formDataFor(opts: {
  content_profile: string;
  aspect_ratio: string;
  target_clips: number;
  source?: "url" | "upload";
}): FormData {
  const fd = new FormData();
  if (opts.source === "upload") {
    fd.set("source_upload_key", "uploads/matrix-file.mp4");
  } else {
    fd.set("source_url", "https://www.twitch.tv/videos/123456");
  }
  fd.set("display_title", "matrix");
  fd.set("target_clips", String(opts.target_clips));
  fd.set("caption_style", "gaming_impact");
  fd.set("reframe_preset", "fps_game");
  fd.set("content_profile", opts.content_profile);
  fd.set("aspect_ratio", opts.aspect_ratio);
  return fd;
}

describe("create option catalogs", () => {
  it("CONTENT_PROFILE_IDS matches the full product matrix", () => {
    assert.deepEqual([...CONTENT_PROFILE_IDS], [...EXPECTED_PROFILES]);
  });

  it("ASPECT_RATIO_IDS matches the full product matrix", () => {
    assert.deepEqual([...ASPECT_RATIO_IDS], [...EXPECTED_ASPECTS]);
  });
});

describe("create → navigate matrix", () => {
  const assigned: string[] = [];
  const createBodies: unknown[] = [];
  let originalFetch: typeof globalThis.fetch | undefined;

  afterEach(() => {
    if (originalFetch) {
      globalThis.fetch = originalFetch;
      originalFetch = undefined;
    }
    assigned.length = 0;
    createBodies.length = 0;
    // @ts-expect-error test teardown
    delete globalThis.window;
  });

  function stubCreateApi(jobId: string) {
    originalFetch = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      assert.match(url, /\/api\/jobs\/?$/);
      assert.equal(init?.method, "POST");
      createBodies.push(JSON.parse(String(init?.body ?? "{}")));
      return new Response(JSON.stringify({ id: jobId, status: "queued" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }) as typeof fetch;
  }

  function stubWindowAssign() {
    // @ts-expect-error node test stub
    globalThis.window = {
      location: {
        assign(url: string) {
          assigned.push(url);
        },
      },
      sessionStorage: {
        setItem() {},
        getItem() {
          return null;
        },
      },
    };
  }

  for (const content_profile of CONTENT_PROFILE_IDS) {
    for (const aspect_ratio of ASPECT_RATIO_IDS) {
      for (const target_clips of CLIP_COUNTS) {
        const label = `${content_profile} / ${aspect_ratio} / ${target_clips}`;
        it(`create+nav: ${label}`, async () => {
          const jobId = `job-${content_profile}-${aspect_ratio.replace(":", "x")}-c${target_clips}`;
          stubCreateApi(jobId);

          const result = await createJobAction(
            { status: "idle" },
            formDataFor({ content_profile, aspect_ratio, target_clips }),
          );

          assert.equal(result.status, "ok", result.message);
          assert.equal(result.jobId, jobId);

          stubWindowAssign();
          afterCreateJobSuccess(result.jobId!);
          assert.deepEqual(assigned, [`/jobs/${jobId}/`]);
          assert.equal(jobOverviewPath(jobId), `/jobs/${jobId}/`);

          const body = createBodies[0] as {
            content_profile: string;
            aspect_ratio: string;
            target_clips: number;
          };
          assert.equal(createBodies.length, 1);
          assert.equal(body.content_profile, content_profile);
          assert.equal(body.aspect_ratio, aspect_ratio);
          assert.equal(body.target_clips, target_clips);
        });
      }
    }
  }

  it("create+nav: file upload source (friend repro path)", async () => {
    const jobId = "job-upload-gaming-16x9-c1";
    stubCreateApi(jobId);
    const result = await createJobAction(
      { status: "idle" },
      formDataFor({
        content_profile: "gaming",
        aspect_ratio: "16:9",
        target_clips: 1,
        source: "upload",
      }),
    );
    assert.equal(result.status, "ok", result.message);
    stubWindowAssign();
    afterCreateJobSuccess(result.jobId!);
    assert.deepEqual(assigned, [`/jobs/${jobId}/`]);
    const body = createBodies[0] as {
      source_upload_key: string;
      target_clips: number;
      aspect_ratio: string;
    };
    assert.equal(body.source_upload_key, "uploads/matrix-file.mp4");
    assert.equal(body.target_clips, 1);
    assert.equal(body.aspect_ratio, "16:9");
  });
});

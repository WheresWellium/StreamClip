/** Centralized help text for UI legend / info icons. */

export const JOB_STATUS_LEGEND: Record<string, string> = {
  queued: "Job is waiting in the queue to start processing.",
  ingesting: "Downloading or copying the source video into the pipeline.",
  transcribing: "Running speech-to-text on the full source with word timestamps.",
  detecting: "Finding highlight moments using audio, motion, and chat signals.",
  scoring_virality: "Ranking clips against each other for expected platform performance (never blocks output).",
  virality_scored: "Comparative scores applied; clips are being rendered.",
  processing: "Rendering clips — reframe to your aspect ratio, captions, and overlays.",
  done: "All clips finished. Download links are ready.",
  error: "Pipeline failed. See the error message for details.",
  cancelled: "Job was stopped before completion.",
};

export const PIPELINE_STAGE_LEGEND: Record<string, string> = {
  queued: "Waiting to start.",
  ingesting: "Fetching source media.",
  transcribed: "Full transcript saved.",
  detecting: "Scoring highlight candidates.",
  detected: "Clip boundaries chosen.",
  scoring_virality: "Comparative performance scoring per clip.",
  virality_scored: "Clips ranked by how they stack up against each other.",
  reframe: "Auto-reframing to the job's aspect ratio with subject tracking.",
  caption: "Burning word-synced captions.",
  overlay: "Adding meme/GIF overlays.",
  completed: "Pipeline finished.",
  error: "Something went wrong.",
  cancelled: "Stopped by user.",
};

export const EMOTION_LEGEND: Record<string, string> = {
  hype: "High-energy excitement — big plays, celebrations, hype moments.",
  rage: "Frustration or anger — fails, deaths, rage quits.",
  funny: "Comedic or absurd — jokes, unexpected moments.",
  clutch: "Clutch plays — last-second wins, 1vX, close calls.",
  fail: "Funny or painful fails — whiffs, misplays.",
  weird: "Unusual or offbeat — strange audio or odd moments.",
  neutral: "Calm or informational — no strong emotional signal.",
};

export const CLIP_SCORE_LEGEND = {
  rank: "Clip rank after ensemble scoring — #1 is the highest-ranked moment.",
  ensemble:
    "Combined score from comparative rank, audio, novelty, motion, and chat (0–100).",
  duration: "Length of this clip in seconds.",
  hook: "Transcript excerpt — the spoken line viewers hear in the clip.",
  title: "Short label derived from the clip transcript.",
  virality:
    "How this clip should stack up against your other cuts for platform performance. Does not gate creation.",
  audio: "Loudness and energy in this segment.",
  novelty: "Sudden audio changes — reactions, SFX, surprises.",
  motion: "On-screen movement from optical flow analysis.",
};

export const FORM_SECTION_LEGEND = {
  source:
    "Where your video comes from — paste a URL or upload a file. Twitch, YouTube, Kick, and direct uploads are supported.",
  settings:
    "Controls how many clips are created and how they are styled. These are frozen per job when you submit.",
  clips:
    "How many clips to generate (1–20). The pipeline always produces at least one clip.",
  reframe:
    "How the camera crops and tracks subjects for your chosen aspect ratio. HUD-safe zones vary by preset.",
  captions:
    "Caption animation style burned into each clip. Word-level sync aligns text to speech.",
};

export const AUTH_LEGEND = {
  privacy:
    "Signed-in jobs are private to your account. Without signing in, jobs are tied to this browser via a device cookie and are not visible on other devices.",
  email: "Used to sign in and associate jobs with your account.",
  password:
    "At least 8 characters with letters and a number or symbol. Stored hashed — never sent in plain text.",
  displayName: "Shown in your profile; defaults to your email prefix.",
};

export const PROGRESS_LEGEND = {
  bar: "Overall pipeline completion from ingest through render (0–100%).",
  stage: "Current pipeline step. Hover the status badge for what each status means.",
  message: "Human-readable detail about what the worker is doing right now.",
  elapsed: "Wall-clock time since the pipeline started ingesting the source.",
  eta: "Estimated time left for remaining stages. Hidden until source duration is known.",
  stepper: "Major pipeline phases in order. Checkmarks show completed stages with elapsed time.",
  ingestSub: "Download or storage copy progress while the source is being ingested.",
};

/** Canonical pipeline phases shown in the job detail stepper (matches backend ETA stages). */
export const PIPELINE_STEPPER_LEGEND: Record<string, string> = {
  ingest: "Download or copy the source video and probe metadata.",
  transcribe: "Speech-to-text with word-level timestamps.",
  highlights: "Find highlight moments from audio, motion, and chat.",
  virality: "Rank clips by how they should stack up on the feed.",
  process_clip: "Reframe to any ratio, caption, and render clips.",
};

export const ERROR_LEGEND = {
  generic:
    "Something unexpected happened. Try again, or use Report a bug in the header if it keeps failing.",
  jobDetail:
    "The job page failed to load or render. Try again — if the job still exists, progress may continue on the server.",
};

/** Grouped help strings for components that prefer a single import. */
export const help = {
  errors: ERROR_LEGEND,
};

export function legendForStatus(status: string): string {
  return JOB_STATUS_LEGEND[status] ?? "Current job status in the pipeline.";
}

export function legendForStage(stage: string): string {
  const base = stage.split("/")[0];
  return PIPELINE_STAGE_LEGEND[stage] ?? PIPELINE_STAGE_LEGEND[base] ?? `Pipeline stage: ${stage}`;
}

export function legendForPipelineStep(stepKey: string): string {
  return PIPELINE_STEPPER_LEGEND[stepKey] ?? `Pipeline phase: ${stepKey}`;
}

export function legendForEmotion(emotion: string): string {
  return EMOTION_LEGEND[emotion] ?? "Detected emotional tone of this clip.";
}

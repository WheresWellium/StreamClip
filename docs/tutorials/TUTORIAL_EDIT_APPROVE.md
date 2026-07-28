# Tutorial — Edit & Approve Clips

**Time:** ~10 minutes · **Prerequisite:** [First job](TUTORIAL_FIRST_JOB.md) with at least one **done** clip

Review AI-generated clips, adjust title and trim boundaries, fix transcript words, then **approve** clips you want to publish or save.

---

## Overview

| Edit | Where | Saved when |
|------|-------|------------|
| Title / hook | Clip editor header | **Save** |
| Trim in/out | Timeline slider | **Save** (re-render) |
| Transcript words | Transcript panel | **Save** |
| Approval | Clip card or editor | **Approve** (instant) |

Only **approved** clips can be published or batch-published. See [Beta quickstart](../BETA_TESTER_QUICKSTART.md).

---

## Step 1 — Open a finished clip

1. Go to your **job detail** page (from home → click the job)
2. Click a clip with status **done** and a playable preview
3. The **clip editor** opens with video preview on the left, controls on the right

!!! tip
    If preview shows "Showing last render — save to apply trim", your trim edits are staged but not yet rendered.

---

## Step 2 — Edit the title

1. Find the **Title** field at the top of the editor
2. Replace the auto-generated title with something platform-friendly (≤100 chars works well for Shorts)
3. Optionally edit the **Hook** line — this feeds caption overlays

Title is required before save. Empty titles block **Save**.

---

## Step 3 — Trim start and end

1. Scroll to the **Trim timeline** section
2. Drag the **start** and **end** handles, or type seconds in the numeric inputs
3. Preview updates to show the trimmed region
4. Click **Save**

Trim changes trigger a **re-render**. Progress appears on the clip card until the new file is ready.

!!! warning "Trim limits"
    Trim end cannot exceed the source clip duration. The editor shows the max allowed seconds.

---

## Step 4 — Fix transcript words

1. Open the **Transcript** panel in the editor
2. Click individual words to edit spelling or wording
3. Edited words are highlighted — useful for names, game titles, and slang the ASR misheard
4. Click **Save** to persist `transcript_edits` with the clip

Transcript edits affect on-screen captions on the next render. You do not need to re-trim unless timing changed.

!!! info "Full transcript vs. clip transcript"
    The job page **Show transcript** on clip cards is read-only. Word-level edits happen only in the clip editor.

---

## Step 5 — Save and wait for render

1. Click **Save** (bottom of editor or toolbar)
2. Watch the clip status — it may briefly return to **processing** during re-render
3. When preview updates with your changes, edits are applied

Use **Discard** to revert unsaved changes.

---

## Step 6 — Approve the clip

1. On the clip card or in the editor, click **Approve**
2. Toast confirms: *"Ready to publish, schedule, or save to Vault."*
3. Approved clips show an **approved** badge in the job grid

You can **unapprove** later if you change your mind (same button toggles).

---

## Step 7 — Batch actions (optional)

From the job toolbar when multiple clips are approved:

- **Publish approved (N)** — queues all approved clips to a connected platform
- Requires distribution connected — see [Publish YouTube](TUTORIAL_PUBLISH_YOUTUBE.md)

---

## Acceptance checklist (T0-3)

**Acceptance checklist:**

- [ ] Patched title and trim boundaries
- [ ] At least one transcript word edit saved
- [ ] Clip approved successfully

---

## Next steps

| Goal | Tutorial |
|------|----------|
| Long-term storage | [Vault](TUTORIAL_VAULT.md) |
| YouTube Shorts | [Publish YouTube](TUTORIAL_PUBLISH_YOUTUBE.md) |

---

*See also: [Beta quickstart](../BETA_TESTER_QUICKSTART.md) · [Known issues](../BETA_KNOWN_ISSUES.md)*

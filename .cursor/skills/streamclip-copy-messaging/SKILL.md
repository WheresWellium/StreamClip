---
name: streamclip-copy-messaging
description: >-
  Authors and reviews qClip product copy and UX messaging.
  Positions the product as an all-in-one clip studio for any creator — long,
  medium, or short form — with auto-reframe to any aspect ratio and comparative
  virality scores. Use when editing hero headlines, onboarding, create-job form,
  legends, tooltips, or any user-facing text that frames who the product is for.
---

# qClip Copy & Messaging

Product UI brand: **qClip**. Repo folder may still be `streamclip`; technical env prefixes may still use `STREAMCLIP_*` — user-facing copy is always **qClip**.

## Product positioning

qClip is the **all-in-one clip studio for creators** — not a “viral shorts factory” and not a streamers-only tool.

It helps anyone who makes video (podcasts, uploads, VODs, streams, short clips) **cut the good parts, reframe to any aspect ratio, and rank what to ship first**. Virality score is a **comparative performance signal** across your clips for a platform — not a promise that something will go viral.

### One-line pitch (internal)

> Clip any length. Frame any ratio. Rank what wins.

### Brand pillars (lead with these)

1. **Any length** — long, medium, and short-form sources are first-class
2. **Any ratio** — auto-reframe to vertical, square, portrait, landscape (not 9:16-only)
3. **Ranked to ship** — virality / ensemble scores show how clips stack up against each other
4. **One studio, not a stack** — find moments, caption, overlay, vault, publish, schedule in one product (no other platform packs this many creator tools together)

### Audience

**Any content creator** who wants an easy clip workflow. Twitch/stream features (chat spikes, VOD URLs, gaming presets) are **one lane**, never the whole identity.

## Preferred hero headline (verbatim)

Use this on the marketing / app hero unless the user specifies otherwise:

> **Clip any length. Frame any ratio. Rank what wins.**

Accent the second beat in brand color when the layout allows (e.g. `Frame any ratio` or `Rank what wins` in `text-sky-400`).

Current implementation: `web/app/page.tsx`.

### Preferred hero subtext

> Paste a URL or upload a file. qClip finds the moments, reframes to any aspect ratio, and scores each clip so you know which cuts should outperform the rest.

### Preferred meta description

> All-in-one clip studio — cut any length of video, auto-reframe to any aspect ratio, and rank clips by how they should stack up on the feed.

## Messaging matrix

| Surface | Preferred framing | Avoid |
|---------|-------------------|-------|
| Hero (`web/app/page.tsx`) | Any length · any ratio · ranked to ship | “Viral vertical shorts” as the whole product |
| Hero subtext | URL or upload; reframe any ratio; comparative scores | Twitch-only examples; “vertical clips out” as the only outcome |
| Create job (`create-job-form.tsx`) | “Paste a URL or upload a video” + social-ready / any-ratio clips | Implying live stream or 9:16-only required |
| Onboarding (`onboarding-wizard.tsx`) | Align with hero pillars | “Long-form streams into vertical clips” |
| Virality / scores (`legends.ts`, clip cards) | Comparative rank — how clips stack up for platform performance | “Go viral” guarantees; virality as the product’s sole purpose |
| Reframe / aspect ratio | Auto-reframe to **any** aspect ratio | Hard-coding “9:16 vertical” as the only output story |
| README / docs | Broader than Twitch; full studio feature set | Leading with “5-hour Twitch VOD” as sole identity |
| Distribution / Vault | “Publish”, “Schedule”, “Save to Clip Vault” | Confusing Clip Vault with asset/meme library |

## Inclusive source types

When describing inputs, include:

- Public video URLs (VOD, podcast video, YouTube, etc.)
- Direct file upload
- Short-form and medium-form sources (not only multi-hour VODs)
- Twitch/stream URLs **as one option**, not the only option

Content profiles (`podcast`, gaming, etc.) in `create-job-form.tsx` already support non-stream use cases — copy should match.

## Where copy lives

| File | Content |
|------|---------|
| `web/app/page.tsx` | Hero badge, headline, subtext |
| `web/app/layout.tsx` | `<title>`, nav brand |
| `web/lib/loading/defaults.ts` | Boot screen title |
| `web/components/onboarding/onboarding-wizard.tsx` | Welcome step |
| `web/components/jobs/create-job-form.tsx` | Create job labels |
| `web/lib/legends.ts` | Score / virality tooltips |

## Review checklist

Before shipping user-facing copy:

1. Brand name is **qClip** (not StreamClip or Jet Stream)
2. Hero uses the three pillars (length, ratio, rank)
3. No “go viral” guarantees
4. Stream/Twitch mentioned as one lane, not the whole product
5. Installer / desktop references use **qClip-Setup-win-x64.exe**

---
name: streamclip-copy-messaging
description: >-
  Authors and reviews StreamClip product copy and UX messaging. Positions the
  product as long-form video to viral vertical shorts (not streamers-only).
  Use when editing hero headlines, onboarding, create-job form, legends,
  tooltips, or any user-facing text that frames who StreamClip is for.
---

# StreamClip Copy & Messaging

## Product positioning

StreamClip turns **long-form video into viral vertical shorts** — for podcasts, uploads, VOD URLs, and streams alike. It is **not** a streamers-only tool unless the copy is explicitly about Twitch-specific features (chat signal, Twitch URLs).

## Preferred hero headline (verbatim)

Use this on the marketing hero unless the user specifies otherwise:

> **Turn long-form video into viral vertical shorts**

Current implementation: `web/app/page.tsx` (h1 with `viral vertical shorts` in accent color).

## Messaging matrix

| Surface | Preferred framing | Avoid |
|---------|-------------------|-------|
| Hero (`web/app/page.tsx`) | Long-form video → viral vertical shorts | "Streams only", "for streamers" |
| Hero subtext | Paste URL or upload; captions, reframe, overlays | Twitch-only examples as the default |
| Create job (`create-job-form.tsx`) | "Paste a URL or upload a video" | Implying live stream required |
| Onboarding (`onboarding-wizard.tsx`) | Align with hero — **update** "long-form streams" → "long-form video" when touching that file | Stream-centric welcome copy |
| README | Broader than Twitch; Twitch is one ingest source | Leading with "5-hour Twitch VOD" as sole identity |
| Distribution / Vault | "Publish", "Schedule", "Save to Clip Vault" | Confusing Clip Vault with asset/meme library |

## Inclusive source types

When describing inputs, include:

- Public video URLs (VOD, podcast video, YouTube, etc.)
- Direct file upload
- Twitch/stream URLs **as one option**, not the only option

Content profiles (`podcast`, gaming, etc.) in `create-job-form.tsx` already support non-stream use cases — copy should match.

## Where copy lives

| File | Content |
|------|---------|
| `web/app/page.tsx` | Hero headline + subtext |
| `web/components/jobs/create-job-form.tsx` | Card title, description, URL/upload labels |
| `web/components/onboarding/onboarding-wizard.tsx` | Welcome step |
| `web/lib/help/legends.ts` | Tooltip/legend strings (status, pipeline, scores) |
| `web/components/clips/clip-destinations-drawer.tsx` | Publish/schedule/vault labels |
| `web/components/distribution/*.tsx` | Connections, queue, Pro gate copy |
| `README.md` | User-facing overview (align gradually with positioning) |

## Copy guidelines

1. **Lead with outcome** — vertical shorts ready to post, not pipeline jargon
2. **Inclusive inputs** — URL + upload before niche sources
3. **Twitch when specific** — chat spikes, VOD URLs, gaming presets only in Twitch/gaming context
4. **Clip Vault naming** — always "Clip Vault"; asset library is "assets" / overlays
5. **Pro gates** — explain value ("publish to YouTube/TikTok") not punishment
6. **Short sentences** — match existing Tailwind UI tone (confident, technical-friendly)

## Review checklist

When editing user-facing copy:

```
Copy review:
- [ ] Hero/subtext inclusive of non-stream sources?
- [ ] No accidental "streams only" framing?
- [ ] Clip Vault ≠ asset vault in labels?
- [ ] Tooltips in legends.ts if new concepts need help?
- [ ] Error messages actionable (match StreamClipError user_message style)?
```

## Examples

**Good (create job description)**

> Paste a URL or upload a video — we'll find the best moments and render vertical clips.

**Avoid**

> Paste your Twitch stream URL to clip your broadcast.

**Good (distribution)**

> Publish approved clips to YouTube Shorts or schedule for later.

**Avoid**

> Send your stream highlights to social media.

## Related

| Skill | When |
|-------|------|
| [streamclip-development](../streamclip-development/SKILL.md) | Web patterns, `legends.ts` location |
| [streamclip-social-distribution](../streamclip-social-distribution/SKILL.md) | Destination UX terminology |
| [streamclip-gap-analysis](../streamclip-gap-analysis/SKILL.md) | UX journey audit |

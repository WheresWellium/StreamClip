---
name: streamclip-copy-messaging
description: >-
  Authors and reviews StreamClip / Jet Stream product copy and UX messaging.
  Positions the product as an all-in-one clip studio for any creator — long,
  medium, or short form — with auto-reframe to any aspect ratio and comparative
  virality scores. Use when editing hero headlines, onboarding, create-job form,
  legends, tooltips, or any user-facing text that frames who the product is for.
---

# StreamClip Copy & Messaging

Product UI brand: **Jet Stream**. Repo / docs may still say StreamClip — keep UI-facing copy on Jet Stream unless the user asks otherwise.

## Product positioning

Jet Stream is the **all-in-one clip studio for creators** — not a “viral shorts factory” and not a streamers-only tool.

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

> Paste a URL or upload a file. Jet Stream finds the moments, reframes to any aspect ratio, and scores each clip so you know which cuts should outperform the rest.

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
| `web/app/page.tsx` | Hero headline + subtext + home cards |
| `web/app/layout.tsx` | Title + meta description |
| `web/components/jobs/create-job-form.tsx` | Card title, description, URL/upload labels |
| `web/app/jobs/new/page.tsx` | New-job page intro |
| `web/components/onboarding/onboarding-wizard.tsx` | Welcome step |
| `web/lib/help/legends.ts` | Tooltip/legend strings (status, pipeline, scores, reframe) |
| `web/components/clips/clip-destinations-drawer.tsx` | Publish/schedule/vault labels |
| `web/components/distribution/*.tsx` | Connections, queue, Pro gate copy |
| `README.md` | User-facing overview (align gradually with positioning) |

## Voice & phrasing

**Tone:** Confident, specific, slightly sharp — creator-tool energy, not SaaS fluff.

**Do**

- Lead with **outcome + control**: cut, frame, rank, ship
- Name the differentiator: **any length · any ratio · ranked clips · full studio**
- Keep sentences short; match existing Tailwind UI tone
- Call the score what it is: **how clips stack up** / **which cuts to ship first**
- Use “clip studio”, “ranked to ship”, “any ratio”, “any length” as signature phrases

**Don’t**

- Tunnel-vision on “viral” or “vertical shorts” as the brand
- Promise virality (“guaranteed to go viral”)
- Default every sentence to streamers / Twitch
- Sound like every other AI clipper (“turn your streams into viral Shorts”)
- Confuse **Clip Vault** (saved clips) with **assets** / overlays

### Signature phrases (reuse)

| Phrase | Use for |
|--------|---------|
| Clip any length | Hero, onboarding, README |
| Frame any ratio | Hero, reframe help, aspect-ratio UI |
| Rank what wins | Hero, score tooltips, review step |
| Ranked to ship | Subheads, distribution intros |
| All-in-one clip studio | Meta, Pro gates, README |
| Stack up on the feed | Virality score explanations |

## Virality score — canonical framing

Virality score is **comparative**, not prophetic:

> Ranks this clip against your other cuts for expected platform performance — so you ship the strongest ones first. It never blocks creation.

Ensemble / rank copy should reinforce “stack up against each other,” not “will go viral.”

## Copy guidelines

1. **Lead with creator outcome** — easy clips from any length, framed for the destination, ranked to ship
2. **Any ratio, not vertical-only** — mention auto-reframe / aspect ratio when talking about output
3. **Inclusive inputs** — URL + upload before niche sources; long / medium / short all welcome
4. **Twitch when specific** — chat spikes, VOD URLs, gaming presets only in Twitch/gaming context
5. **Clip Vault naming** — always “Clip Vault”; asset library is “assets” / overlays
6. **Pro gates** — explain value (“publish to YouTube/TikTok”, full studio) not punishment
7. **Short, catchy, specific** — prefer signature phrases over generic AI-clipper clichés

## Review checklist

When editing user-facing copy:

```
Copy review:
- [ ] Any-length framing (not long-form-only)?
- [ ] Any-ratio / auto-reframe mentioned where output is described?
- [ ] Virality framed as comparative rank, not “go viral”?
- [ ] Not tunnel-visioned on vertical shorts as the whole product?
- [ ] Inclusive of non-stream sources (no accidental “streams only”)?
- [ ] Clip Vault ≠ asset vault in labels?
- [ ] Sounds like Jet Stream (specific, catchy) — not generic AI clipper copy?
- [ ] Tooltips in legends.ts if new concepts need help?
- [ ] Error messages actionable (match StreamClipError user_message style)?
```

## Examples

**Good (hero)**

> Clip any length. Frame any ratio. Rank what wins.

**Avoid**

> Turn long-form video into viral vertical shorts.

**Good (create job description)**

> Paste a URL or upload a video — we find the best moments, reframe to any aspect ratio, and rank clips so you know what to ship first.

**Avoid**

> Paste your Twitch stream URL to clip your broadcast into viral Shorts.

**Good (virality tooltip)**

> How this clip should stack up against your other cuts for platform performance. Does not gate creation.

**Avoid**

> Predicted chance this clip goes viral.

**Good (distribution)**

> Publish ranked clips to YouTube, TikTok, or schedule for later — vault the rest.

**Avoid**

> Send your stream highlights to social media.

**Good (onboarding)**

> Welcome to Jet Stream — the clip studio for any length of footage. Auto-reframe to any ratio, caption and overlay in one pass, then rank what wins before you publish.

**Avoid**

> Turn long-form streams into vertical clips with AI.

## Related

| Skill | When |
|-------|------|
| [streamclip-development](../streamclip-development/SKILL.md) | Web patterns, `legends.ts` location |
| [streamclip-social-distribution](../streamclip-social-distribution/SKILL.md) | Destination UX terminology |
| [streamclip-gap-analysis](../streamclip-gap-analysis/SKILL.md) | UX journey audit |

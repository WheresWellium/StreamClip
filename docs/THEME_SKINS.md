# StreamClip Theme Skins

Five executive-level Figma design system skins for the in-app theme switcher. Each skin lives in its own Figma file with identical page structure.

**Typography (all skins):** Space Grotesk + JetBrains Mono  
**Governance:** Figma-only — no production code until sign-off.

---

## Master Index

| # | Skin | Slug | Figma URL | File Key |
|---|------|------|-----------|----------|
| 1 | Tape Maroon Manga | `tape-maroon-manga` | [Open in Figma](https://www.figma.com/design/h7gWNvmKOkn4eG9qYhmpql/StreamClip-Design-System-v3-Tape-Maroon-Manga) | `h7gWNvmKOkn4eG9qYhmpql` |
| 2 | Warm Tape Parlor | `warm-tape-parlor` | [Open in Figma](https://www.figma.com/design/YNC1P3ttppxui88kLfB4TU/StreamClip-Theme-Warm-Tape-Parlor) | `YNC1P3ttppxui88kLfB4TU` |
| 3 | Midnight Lounge | `midnight-lounge` | [Open in Figma](https://www.figma.com/design/vW0k1WSeEoTRMNPB2QjWUG/StreamClip-Theme-Midnight-Lounge) | `vW0k1WSeEoTRMNPB2QjWUG` |
| 4 | Signal Cathedral | `signal-cathedral` | [Open in Figma](https://www.figma.com/design/NRarnlPtQWmGsdhIilRMYf/StreamClip-Theme-Signal-Cathedral) | `NRarnlPtQWmGsdhIilRMYf` |
| 5 | Kinetic Storm Manga | `kinetic-storm-manga` | [Open in Figma](https://www.figma.com/design/2eHw3cEKm8xJbB4Y15swyR/StreamClip-Theme-Kinetic-Storm-Manga) | `2eHw3cEKm8xJbB4Y15swyR` |

**State ledger:** `tmp/dsb-state-streamclip-themes.json`

---

## Theme 1 — Tape Maroon Manga

- **Slug:** `tape-maroon-manga`
- **Emotion:** Warm tape nostalgia meets manga pop energy
- **Shape:** 8px radius · 2px maroon borders · Ben-Day halftone · katakana accents
- **Palette:** cream `#FAF6F0`, maroon `#7A2838`, rose `#C97068`, sage `#8B9E7E`, ink `#2C1810`
- **When to use:** Default StreamClip skin — creator-facing flows, onboarding, viral clip moments
- **Theme switcher:** `data-theme="tape-maroon-manga"`

---

## Theme 2 — Warm Tape Parlor

- **Slug:** `warm-tape-parlor`
- **Emotion:** Cozy editorial vinyl lounge — espresso, cream, dusty rose
- **Shape:** 12px soft radius · 1px subtle borders · gentle drop shadows · no halftone
- **Palette:** cream `#F0E4D7`, espresso `#1A1210`, burgundy `#6B3A42`, dustyRose `#C49994`, sage `#7A9E86`, softGold `#C9B896`
- **When to use:** Settings, premium onboarding, editorial content, comfort-first UX
- **Theme switcher:** `data-theme="warm-tape-parlor"`

---

## Theme 3 — Midnight Lounge

- **Slug:** `midnight-lounge`
- **Emotion:** Warm dark luxury — burgundy velvet + teal glow, vinyl stacks, intimate
- **Shape:** 8px radius · teal glow accents · dark velvet surfaces
- **Palette:** void `#140E12`, burgundy `#4A2230`, tealGlow `#3A8B82`, cream `#F5EDE8`, rose `#B87A72`, gold `#BFA56A`
- **When to use:** Night mode, power-user dashboards, premium tier, late-night streaming
- **Theme switcher:** `data-theme="midnight-lounge"`

---

## Theme 4 — Signal Cathedral

- **Slug:** `signal-cathedral`
- **Emotion:** Cinematic awe — teal void, fuchsia watermark, emerald CTA, monumental typography
- **Shape:** 4px minimal radius · hairline borders · fuchsia halo rings
- **Palette:** tealDeep `#081518`, tealCathedral `#0C3129`, fuchsia `#D63AEE`, emerald `#10B77F`, muted `#607577`, cream `#F5F5F0`
- **When to use:** Hero moments, launch pages, cinematic job completion, marketing surfaces
- **Theme switcher:** `data-theme="signal-cathedral"`

---

## Theme 5 — Kinetic Storm Manga

- **Slug:** `kinetic-storm-manga`
- **Emotion:** Japanese pop art energy — paper ground, ink borders, Ben-Day dots, katakana, vermillion/cobalt/lemon
- **Shape:** 0–2px sharp corners · 3px ink borders · halftone · NO orange
- **Palette:** paper `#FAFAFA`, ink `#0A0A0A`, vermillion `#E63B2E`, cobalt `#2563EB`, lemon `#FFE600`
- **When to use:** Viral marketing, Gen-Z creator flows, hype moments, social share surfaces
- **Theme switcher:** `data-theme="kinetic-storm-manga"`

---

## Shared File Structure (per skin)

| Page | Contents |
|------|----------|
| Cover | Hero — theme name, slug, emotional one-liner, signature visual |
| Foundations | Color swatches, typography, shape language, spacing scale, emotion→color mapping |
| Components | 19 vertical sections (34 components) — zero overlap layout |
| Screens | Home/New Job, Job Progress, Vault Grid, Clip Detail + Drawer |
| Motion | 4 specs with duration/easing + SFX placeholders |
| Theme Index | Slug, CSS token preview, when-to-use, contrast notes |

## Theme Switcher Notes

- Apply via `data-theme="<slug>"` on root element
- Each file ships a CSS token preview block on the **Theme Index** page
- Component names are consistent across skins for Code Connect / implementation mapping
- Screens use `AppShell/default` **instance** + sibling `MainZone` frame (instances cannot nest MainZone)

## Component Inventory (all skins)

Alert/info · AppShell/default · Avatar/sm|md|lg · Badge/viral|hype|sage|rose · Button/primary|secondary|accent|ghost · Card/Clip · Card/Job · Dialog/confirm · Drawer/right · EmptyState/default · Input/default · InputField/default · Modal/default · NavItem/default|active · Pipeline/ingest|transcribe|highlights|virality|render · ProgressBar/default · Select/default · Skeleton/card · Toast/success|error · Tooltip/default

---

## Parity Contract

All five skins share **identical structure** with **unique visual art direction**. Implementers and AI agents should rely on this contract for cross-skin mapping.

**Audit status:** `parityAudit: pass` (2026-07-08) — ledger: `tmp/dsb-state-streamclip-themes.json`

### Pages (exact order)

`Cover` → `Foundations` → `Components` → `Screens` → `Motion` → `Theme Index`

### Foundations sections (6)

1. `Color — Primary`
2. `Color — Accents`
3. `Shape Language`
4. `Typography`
5. `Spacing Scale`
6. `Emotion Mapping`

### Components page (19 sections, vertical stack)

Layout: `PAGE_X=80`, `GAP=96`, section width `1440`, zero overlap.

`§ Button` · `§ Badge` · `§ Input` · `§ InputField` · `§ Select` · `§ Card` · `§ Avatar` · `§ NavItem` · `§ Toast` · `§ Alert` · `§ Tooltip` · `§ ProgressBar` · `§ Pipeline` · `§ Skeleton` · `§ EmptyState` · `§ Modal` · `§ Drawer` · `§ Dialog` · `§ AppShell`

### Component symbols (34, exact names)

See `componentList` in `tmp/dsb-state-streamclip-themes.json`.

### Screens (4 sections)

1. `Screen — Home / New Job`
2. `Screen — Job Progress`
3. `Screen — Vault / Clips Grid`
4. `Screen — Clip Detail Drawer`

Each screen: `AppShell/default` **instance** + sibling `MainZone` frame (`1200×900` at `x+240`).

### Motion (4 sections)

1. `Motion — Panel Enter`
2. `Motion — Viral Badge Pop`
3. `Motion — Pipeline Stage`
4. `Motion — Toast`

### Theme Index (required fields)

- Slug
- Emotion one-liner
- Corner radius + border weight
- CSS token preview block (8 semantic tokens)
- Contrast / WCAG notes
- Component count: **34**
- Screen count: **4**

### Visual uniqueness (do not homogenize)

| Skin | Shape / personality |
|------|---------------------|
| tape-maroon-manga | 8px · 2px maroon borders · Ben-Day · katakana |
| warm-tape-parlor | 12px · soft shadows · espresso/cream/burgundy/rose/sage/gold |
| midnight-lounge | 8px · dark velvet · burgundy + teal glow |
| signal-cathedral | 4px · teal void · fuchsia halos · emerald CTA |
| kinetic-storm-manga | 0–2px sharp · 3px ink · vermillion/cobalt/lemon · NO orange |

**Typography (all skins):** Space Grotesk + JetBrains Mono only.

---

## Figma page structure (each skin file)

| Page | Contents |
|------|----------|
| Cover | Hero — theme name, slug, emotional one-liner, signature visual |
| Foundations | Palette, typography, shape language, spacing, emotion→color mapping |
| Components | 19 sections · 34 components (Button, Badge, Input, InputField, Select, Card, Avatar, NavItem, Toast, Alert, Tooltip, ProgressBar, Pipeline, Skeleton, EmptyState, Modal, Dialog, Drawer, AppShell) |
| Screens | New Job, Job Progress, Vault Grid, Clip Detail Drawer |
| Motion | Panel enter, badge pop, pipeline, toast (SFX placeholders) |
| Theme Index | Slug, CSS tokens, when-to-use, contrast notes |

## Archived — v2 Industrial Manga

- **File:** [StreamClip Design System v2](https://www.figma.com/design/xOMtagKsZ5bMLnWYX9jKcq/StreamClip-Design-System-v2)
- **File key:** `xOMtagKsZ5bMLnWYX9jKcq`
- **Status:** Superseded — rejected “too corner” CEO feel
- **State ledger:** `tmp/dsb-state-streamclip-v2.json`

**Related:** architecture FigJam boards live in [`design/FIGMA_LINKS.md`](design/FIGMA_LINKS.md).

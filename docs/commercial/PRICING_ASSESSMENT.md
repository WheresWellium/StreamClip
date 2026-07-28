# StreamClip — Pricing Assessment

**Audience:** Board / executive · **Date:** 2026-07-28  
**Constraint:** Recommendations stay within the **settled buy-once perpetual model** — no subscription pivot.

---

## Executive summary

StreamClip’s pricing power comes from **buyer-supplied GPU compute** (near-zero marginal cost per clip for StreamClip) and a market where comparable automation tools charge **$174–1,159/year** in subscriptions. A perpetual **Self-Hosted Pro** SKU priced in the **$129–249** band (3 seats) captures **positive ROI vs SaaS in year 1–2** for target creators while preserving room for **add-on SKUs** and **major-version upgrades**.

**Recommended board scenario for Phase 1 paid launch:** **$179 Self-Hosted Pro perpetual** (3 seats) + **$39 Audio Ingest add-on** + **25% beta lifetime discount** for Phase 0 cohort.

---

## 1. Pricing anchor math

### 1.1 Competitor subscription LTV (perpetual comparison baseline)

| Anchor | Annual price | 3-year LTV | 5-year LTV | Notes |
|--------|-------------|------------|------------|-------|
| Opus Pro (annual) | **~$174** | **~$522** | **~$870** | 300 source min/mo cap |
| Vizard Creator (annual) | **~$174** | **~$522** | **~$870** | 600 min/mo — best $/min SaaS |
| Opus Starter (annual est.) | **~$90** | **~$270** | **~$450** | Entry creator |
| Munch Pro (annual) | **~$490** | **~$1,470** | **~$2,450** | 200 upload min/mo |
| Munch Elite (annual) | **~$1,159** | **~$3,477** | **~$5,796** | 500 upload min/mo |
| Klipr Pro (annual) | **~$490** | **~$1,470** | **~$2,450** | Flat 75 h/mo |
| Descript Creator (annual) | **~$288** | **~$864** | **~$1,440** | Different workflow |
| Submagic Pro + Magic Clips (annual) | **~$420** | **~$1,260** | **~$2,100** | Caption-first |

**Interpretation:** A perpetual price **below ~$520** beats Opus/Vizard **within 3 years** without arguing minute caps. A price **below ~$1,160** beats Munch Elite **within 1 year** for the same persona.

### 1.2 Topaz Gigapixel comparable (buy-once precedent)

StreamClip’s beta plan explicitly references a **Gigapixel-style one-time purchase** (`docs/BETA_TESTER_PLAN.md` §1, §5.3).

| Reference | Price | Status 2026 |
|-----------|-------|-------------|
| Historical Gigapixel perpetual | **~$99** one-time | Widely cited in GTM docs |
| Current Topaz Gigapixel | ~$149/yr subscription | Topaz moved subscription-first Sept/Oct 2025 |

**Board use:** Cite **$99** as the **psychological anchor** for “serious creative software you own,” while noting Topaz’s subscription shift ** strengthens StreamClip’s differentiation** as a remaining buy-once GPU product.

### 1.3 Effective $/minute (SaaS vs StreamClip)

| Model | Effective cost at 300 min/mo | At 500 min/mo |
|-------|------------------------------|---------------|
| Opus Pro | ~$0.58/min ($174/300) | Requires upgrade |
| Munch Elite | ~$2.32/min ($1,159/500) | Tier ceiling |
| StreamClip Pro (self-host) | **~$0** marginal | **~$0** marginal (10k min guardrail) |

---

## 2. Cost-side analysis (StreamClip)

| Cost bucket | Who pays | StreamClip COGS |
|-------------|----------|-----------------|
| GPU / electricity | Buyer | **$0** |
| Whisper / YOLO inference | Buyer hardware | **$0** |
| LLM virality / titles | Buyer API key (Ollama/OpenAI) | **$0** |
| Lemon Squeezy fees | StreamClip | ~5% + $0.50 per sale |
| Support | StreamClip | Scales with cohort, not minutes |
| OAuth / platform APIs | Buyer BYO apps | **$0** for StreamClip |

**Implication:** Price is bounded by **value capture vs SaaS LTV**, not cloud COGS. High-volume users are **margin-accretive** at any fixed perpetual price.

---

## 3. Self-Hosted Pro price band scenarios

**SKU definition (proposed):** Perpetual license · **3 device seats** · Docker prod bundle + distribution hub + desktop entitlement · Lemon Squeezy one-time variant (`core/config.py` → `lemon_squeezy_pro_variant_id`).

| Scenario | Price (USD) | 3-seat implied | Rationale | Risk |
|----------|-------------|----------------|-----------|------|
| **A — Gigapixel anchor** | **$99** | ~$33/seat | Maximum conversion; under 1× Opus annual; strong beta word-of-mouth | Undervalues Pro publish hub; weak funding for support/signing |
| **B — Opus-parity** | **$149** | ~$50/seat | ~1× Opus Pro annual; easy “pays for itself in a year” story | May feel high vs $99 creative anchor without trial |
| **C — Recommended launch** | **$179** | ~$60/seat | Between Opus 1-yr and 2-yr LTV; room for sales/discounts | Balanced |
| **D — Power creator** | **$249** | ~$83/seat | Still < Munch Pro annual; captures podcast/network willingness | Slower Phase 1 conversion |
| **E — Agency floor** | **$399** | ~$133/seat | Klipr Creator annual ×2; precedes future seat packs | Needs stronger publish (TikTok/Reels) to justify |

### Recommended band for board decision

| Phase | Range | Default pick |
|-------|-------|--------------|
| Phase 1 paid beta | **$129–199** | **$179** |
| Public launch (post-signing) | **$149–249** | **$199** list with launch promo at $179 |

**Do not publish a single final number until:** LS product variant created, one real test purchase verified (`docs/BETA_TESTER_PLAN.md` §4.5, §8).

---

## 4. Add-on SKU pricing

Plumbing exists for **audio ingest** (`core/commerce/entitlements.py` — `audio_ingest_variant_ids`, `order_id_tags_audio_ingest`). Title LLM is shipped but not separately gated (`core/title_suggestions.py`).

| Add-on | Shipped | Suggested one-time | Anchor | Notes |
|--------|---------|-------------------|--------|-------|
| **Audio Ingest** (podcast/VO → clip) | Yes | **$29–49** | Descript minute packs / Klap Starter annual fraction | Bundle at **$39** with Pro for Phase 1 |
| **Clip Title Pro pack** (future gate) | API yes, gate no | **$19–29** | Submagic hook titles ($39/mo sub) | Optional bundle sweetener |
| **Extra seat pack (+3 machines)** | Not built | **$49–79** | Opus seat packs / Klipr workspace math | Requires license server policy |
| **Major version upgrade** | Policy TBD | **40–50% of current Pro** | Topaz upgrade ($79/yr extension cited historically) | See §5 |

**Bundle example (Phase 1):** Pro **$179** + Audio **$39** = **$218** “Creator Complete” (still < 1× Munch Pro annual).

---

## 5. Major-version upgrade policy options

Perpetual licenses need a **renewal revenue** path without becoming subscription.

| Policy | Buyer message | StreamClip revenue | Board pros/cons |
|--------|---------------|-------------------|-----------------|
| **A — Pure perpetual** | “Pay once, updates forever” | Only new customers + add-ons | Simplest GTM; no upgrade revenue |
| **B — Major-version (recommended)** | “Pro 1.x perpetual; 2.0 upgrade optional” | Upgrade SKU ~**$79–99** | Matches `BETA_TESTER_PLAN.md` §5.3; industry norm |
| **C — Included updates N years** | “Includes 2 years of updates” | Converts to B after window | Easier enterprise sales |
| **D — Support subscription (optional)** | “Priority SLA $99/yr” | Recurring optional | Does not violate buy-once for software |

**Recommendation:** **Policy B** — document in `COMMERCIAL.md` at public launch; grandfather beta keys at Pro 1.x + discounted 2.0 upgrade.

---

## 6. Beta cohort discount options

From `docs/BETA_TESTER_PLAN.md` §5.3:

| Option | Mechanism | Discount depth | Best for |
|--------|-----------|----------------|----------|
| **Free Pro during beta** | $0 Lead Magnet / ADMIN variant (`lemon_squeezy_beta_variant_id`) | 100% | Phase 0 technical cohort (current) |
| **Lifetime beta key** | Single-use SCPRO with `entitlement_days: 0` | 100% forever | ≤10 design partners (risk: support load) |
| **25% lifetime lock** | Coupon on paid variant at Phase 1 exit | **$179 → $134** | Recommended — rewards early adopters without full free ride |
| **40% launch window** | 30-day post-Phase-1 coupon | **$179 → $107** | Spike conversion; sunsetting urgency |
| **Credit toward upgrade** | Beta key holders pay **$49** for 2.0 | Loyalty + upgrade path | Pairs with Policy B |

**Recommendation:** Phase 0 keeps **$0 beta**; Phase 1 paid offers **25% lifetime discount** for cohort members who complete T0/T1 flows (`docs/BETA_COHORT_EXIT.md` evidence), plus **40% for 14 days** at Phase 1 open for waitlist.

---

## 7. Scenario summary for board vote

| # | Pro perpetual | Audio add-on | Beta discount | Year-1 revenue target persona | vs Opus Pro 3-yr |
|---|---------------|--------------|---------------|------------------------------|------------------|
| 1 | $99 | $29 | 25% → $74 | Maximum adoption | Saves ~$448 over 3 yr |
| 2 | $149 | $39 | 25% → $112 | Balanced growth | Saves ~$373 over 3 yr |
| **3 (recommended)** | **$179** | **$39** | **25% → $134** | Sustainable Phase 1 | Saves ~$348 over 3 yr |
| 4 | $249 | $49 | None | Premium / post-TikTok GA | Saves ~$273 over 3 yr |

### Sensitivity notes

- **Lowering to $99** accelerates Phase 1 cohort but delays EV signing budget recovery (~$300–500/yr cert + Azure Trusted Signing option per `docs/DESKTOP_SIGNING.md`).
- **Raising above $249** before TikTok direct + Reels + signed desktop is **not supported** by competitive publish parity.
- **Minute caps** on self-host (`core/billing.py`) are product guardrails, not pricing levers — avoid mimicking SaaS credit anxiety; communicate as “fair use.”

---

## 8. What we are not recommending

| Idea | Why excluded |
|------|--------------|
| Monthly subscription | Contradicts settled buy-once strategy and CE narrative |
| Per-minute cloud metering | No hosted GPU product; would mimic weakest competitor trait |
| Freemium cloud render | COGS returns; conflicts with self-host wedge |
| Race to $15/mo | CapEx/support unsustainable; wrong persona |

---

## 9. Implementation checklist (non-code)

1. Create Lemon Squeezy **one-time Pro variant** at board-approved price.
2. Create **Audio Ingest variant** at $39 (or separate bundle product).
3. Update buyer-facing copy in `COMMERCIAL.md` and checkout — **no price in repo today** (intentional).
4. Define **major-version policy** paragraph for `COMMERCIAL.md`.
5. Issue **beta discount codes** tied to cohort exit evidence (`docs/BETA_COHORT_EXIT.md`).
6. Run **one LS test purchase → activate → Shorts publish** before Phase 1 paid invites.

---

## 10. Board ask

Approve a **Phase 1 default list price of $179** (Self-Hosted Pro perpetual, 3 seats) with:

- **$39 Audio Ingest** add-on SKU  
- **25% lifetime beta discount** ($134) for Phase 0 completers  
- **Major-version upgrade** policy B (~$89 for 2.0)  
- Revisit list price to **$199** at public launch once **EV signing + TikTok direct** ship  

---

*Cross-references: `FEATURE_VALUE_INVENTORY.md` · `COMPETITIVE_ANALYSIS.md` · `docs/BETA_TESTER_PLAN.md` §5.3 · `COMMERCIAL.md`*

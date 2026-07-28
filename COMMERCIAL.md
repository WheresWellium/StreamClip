# qClip Commercial License

qClip Community Edition is licensed under the Apache License 2.0 (see [LICENSE](LICENSE)).

The following components require a **qClip Studio** commercial license:

- Desktop installer (`apps/desktop/`)
- Distribution hub platform adapters (YouTube Shorts and TikTok OAuth publish; Instagram Reels is on the roadmap)
- Priority support SLA

## Purchasing

- **Self-Hosted Studio:** One-time purchase via [Lemon Squeezy](https://lemonsqueezy.com) — perpetual entitlement, includes Docker production bundle and license key activation. Keys are delivered by email at purchase (Lemon Squeezy license keys, or qClip's own delivery email on the `order_created` fallback path).
- **Phase 0 beta:** $0 Lead Magnet checkout on the same Lemon Squeezy store — zip + installer downloads and a license key in the receipt. Beta keys activate via the Lemon Squeezy License API on first use (network required once). Operator manual cohort keys use `scripts/import_invite_license.py` before UI activation. See `docs/BETA_DISTRIBUTION.md` (operator runbook).

## Activation

Self-hosted Studio licenses activate at **Settings → License** using a key formatted `SCPRO-XXXX-XXXX-XXXX-XXXX`.

- **Entitlement:** perpetual by default (`licensing.entitlement_days: 0`); a positive value switches to subscription-style expiry.
- **Activations:** up to 3 machines per key (`licensing.max_activations`).
- **Offline grace:** 7 days between entitlement re-verifications (`licensing.offline_grace_days`).

Environment variables for commerce webhooks:

- `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_API_KEY`
- `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_WEBHOOK_SECRET`

For licensing inquiries: licensing@qclip.io

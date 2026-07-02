# StreamClip Commercial License

StreamClip Community Edition is licensed under the Apache License 2.0 (see [LICENSE](LICENSE)).

The following components require a **StreamClip Pro** commercial license:

- Desktop installer (`apps/desktop/`)
- Distribution hub platform adapters (YouTube Shorts, TikTok, Instagram Reels OAuth publish)
- Priority support SLA

## Purchasing

- **Self-Hosted Pro:** Annual license via [Lemon Squeezy](https://lemonsqueezy.com) — includes Docker production bundle and license key activation.
- **StreamClip Cloud:** Managed hosting — monthly subscription via Stripe.

## Activation

Self-hosted Pro licenses activate at **Settings → License** using a key formatted `SCPRO-XXXX-XXXX-XXXX-XXXX`.

Environment variables for commerce webhooks:

- `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_API_KEY`
- `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_WEBHOOK_SECRET`
- `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_STORE_ID`

For licensing inquiries: licensing@streamclip.io

# Active Context

## Current Task
- Deploy pending changes to production (rainbow Absinthe + new Vodka mascot art)

## Done Last Session
- Rainbow Absinthe tier (ELO >= 2100) implemented, committed (4de6f11) — still pending deploy
- Replaced Vodka tier mascot art: user dropped a new bottle image at
  `frontend/public/tiers/vodka.png`, background removed via the same
  corner-seeded flood-fill script used for Absinthe, resized to 320x320,
  saved as `vodka.webp` (overwriting the old one) and the source .png deleted
- Frontend rebuilt clean

## Next Steps
- Commit + push the new vodka.webp
- User deploys to Cloudflare Workers: `export CLOUDFLARE_API_TOKEN="your-token" && cd "/Users/tabby/For work/niddeaw_bmt" && npx wrangler deploy`

## Blockers
- none

## Last Updated
- Claude Code — 2026-08-04

## Checkpoint (auto)
- 02:17 — edited active.md
- 01:55 — edited active.md
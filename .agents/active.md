# Active Context

## Current Task
- User needs to run `npx wrangler deploy` once more to push the just-normalized mascot sizes

## Done Last Session
- Fixed the wrangler.jsonc worker-name mismatch (cfb22a8) — user redeployed
  successfully afterward and confirmed rainbow Absinthe is now live
- User then noticed mascot sizes were visibly inconsistent across the 8
  tiers (screenshot showed Vodka/Absinthe noticeably smaller than the
  other 6). Root cause: each source image had different amounts of
  transparent padding around the character within its 320x320 canvas —
  measured via alpha-channel bounding box (`Image.getbbox()`), Vodka's
  content only filled 72% of canvas height vs ~90% for the rest.
  Normalized all 8 mascots (milk/beer/highball/wine/soju/whisky/vodka/absinthe)
  to the same content height (288px, centered) so they render at visually
  matching sizes everywhere `<TierMascot>` is used.
- Frontend rebuilt clean (JS bundle hash unchanged, only image bytes changed)

## Next Steps
- Commit + push the normalized mascot images
- User runs `npx wrangler deploy` again to push this update

## Blockers
- none

## Last Updated
- Claude Code — 2026-08-04

## Checkpoint (auto)
- 02:46 — edited active.md
- 02:43 — edited active.md
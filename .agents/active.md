# Active Context

## Current Task
- Removed the opaque black background from all 7 tier mascot images per user request — pushing now

## Done Last Session
- Confirmed the mascot image swap was live (previous session)
- User asked to remove the opaque background I'd deliberately kept — redid it properly this time
- Used corner-seeded flood-fill (8 seed points: 4 corners + 4 edge midpoints, threshold 25) instead of a naive per-pixel near-black check — only removes background *connected* to the image edges, so it can't eat into the character's own dark outlines/linework even where those are near-black too. Verified visually on beer/vodka/milk (the trickiest — white/cream character, most background removed at 69%) before applying to all 7 — all clean, no holes or fringing
- Re-exported as WebP with alpha preserved, same tiny file sizes as before (6-12KB each)
- No component code changes needed — TierMascot.vue already just references `/tiers/{tier}.webp`, only the image files changed
- `vite build` clean

## Next Steps
- Push and confirm live

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-23

## Checkpoint (auto)
- 01:11 — edited active.md
- 01:08 — edited active.md
- 01:07 — edited active.md (session completed)
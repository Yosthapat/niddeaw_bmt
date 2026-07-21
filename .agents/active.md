# Active Context

## Current Task
- Fixed /live page: "Up Next" suggestions were showing plain text names with no player avatars, unlike the in-progress section — pushing this fix

## Done Last Session
- Full end-to-end live testing of matchmaking system with 9 real members (session created, all checked in, 5 matches played covering win/loss/draw, ELO/tier updates verified) — nothing deleted per user request
- User spotted via screenshot that LiveView.vue's "คิวถัดไป" (Up Next) suggestions section only rendered team names as plain text, no `PlayerAvatar` — inconsistent with the in-progress section above it and the waiting-queue section below it, both of which already had avatars
- Added `PlayerAvatar` clusters (size md, `-space-x-2` stacking) to the Up Next section, matching the in-progress section's layout exactly
- `vue-tsc -b && vite build` clean

## Next Steps
- Push and confirm live
- Known minor gap from testing: no server-side check preventing an admin from manually pairing a player who's still marked in-progress in another match (only auto-suggest excludes them) — not fixed, flagged for user to decide if it's worth guarding against

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-22

## Checkpoint (auto)
- 02:49 — edited active.md
- 02:48 — edited LiveView.vue
- 02:43 — edited active.md
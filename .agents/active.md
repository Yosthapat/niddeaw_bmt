# Active Context

## Current Task
- Removed the overlapping avatar-stack effect (-space-x-2/-space-x-3 negative margins) across every page that used it, per user request — pushing now

## Done Last Session
- Confirmed live: avatar_url wiring fix for MatchmakingView + BillingView (verified via direct chunk inspection after some stale/transient polling reads)
- User asked to stop member photos from overlapping each other across all pages, specifically flagging /live as an example
- Audited every .vue file for the `-space-x-2`/`-space-x-3` overlapping-avatar-cluster technique — found exactly 3 files: MatchmakingView.vue (admin, 4 clusters), MatchHistoryView.vue (public, 2 clusters), LiveView.vue (public, 4 clusters)
- Replaced `flex -space-x-3` -> `flex gap-2` and `flex -space-x-2` -> `flex gap-1.5` in all of them — avatars in a team cluster now sit side-by-side with a small gap instead of stacked/overlapping
- `vue-tsc -b && vite build` clean

## Next Steps
- Push and confirm live
- Optional: add UI support for singles matches (backend already supports type: 'single')

## Last Updated
- Claude Code — 2026-07-22

## Checkpoint (auto)
- 07:07 — edited active.md
- 07:05 — edited active.md
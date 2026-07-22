# Active Context

## Current Task
- Fixed a real bug in LiveView.vue's polling error handling — pushing now

## Done Last Session
- Cleaned up all 9 test/exploratory matches from this session (5 from the original live-test + 4 created while reviewing the matchmaking UI), reverted all 9 real members to baseline ELO with 0 games played — verified via API
- User asked why /live sometimes shows "โหลดคิวไม่สำเร็จ" (failed to load queue) — direct curl to /api/live returned 200 with valid data, so no server-side bug
- Two likely causes: (1) Render free tier spins down when idle, 30-50s cold-start on first request after a gap; (2) a real client bug — `refresh()` in LiveView.vue set `error.value` unconditionally on ANY failed poll (every 7s), and the template's `v-else-if="error"` fully replaces the page, so a single transient poll failure after a successful load would wipe out already-correct data instead of just retrying quietly
- Fixed #2: `error.value` is now only set if `live.value` is still null (i.e. we've never successfully loaded) — once data has loaded once, a later poll failure is silently ignored and the next poll retries
- Audited the other two `usePolling` users (CheckinView.vue, MatchmakingView.vue) — neither has a try/catch around their refresh function, so a failed poll there just silently no-ops rather than wiping the page; not affected by this bug
- `vue-tsc -b && vite build` clean

## Next Steps
- Push and confirm live

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-22

## Checkpoint (auto)
- 07:33 — edited active.md
- 07:32 — edited LiveView.vue
- 07:24 — edited active.md
- 07:24 — cleanup completed; all 9 matches deleted; database reset
- 07:21 — edited active.md
- 07:18 — edited active.md
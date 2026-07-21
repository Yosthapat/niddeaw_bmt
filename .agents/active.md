# Active Context

## Current Task
- Pushing: bigger player avatars + name-below-avatar layout on /matches and /live, and match format reduced to 2 sets (no 3rd/tiebreaker set)

## Done Last Session
- Cancel-match feature fully verified end-to-end on prod with the real admin token: DELETE on an in-progress throwaway match -> 204, disappeared from `/api/live`; DELETE on an already-completed match -> 409 as designed
- User reviewed `/matches` and `/live` with real member photos now uploaded, asked for: bigger avatars, name moved below the avatar instead of beside it, and only 2 sets per match (no 3rd set)
  - `MatchHistoryView.vue` and `LiveView.vue` (both in-progress and Up Next sections): avatar size `md` -> `lg`, layout changed from horizontal (name beside cluster) to vertical (cluster centered, name below), `-space-x-2` -> `-space-x-3` for the bigger avatars
  - `MatchRecordView.vue`: `sets` ref reduced from 3 rows to 2 — no backend change needed, winner-derivation already just counts sets_won without assuming a fixed count
  - Scoped to the two pages the user screenshotted; MatchmakingView.vue's admin in-progress list and MatchDetailView.vue still use the old horizontal/md layout — offered to extend if wanted
- `vue-tsc -b && vite build` clean

## Next Steps
- Push and confirm live
- If user wants full consistency, extend the same avatar-size/vertical-layout treatment to MatchmakingView.vue (admin) and MatchDetailView.vue too

## Blockers
- None

## Last Updated
- Claude Code — 2026-07-22

## Checkpoint (auto)
- 03:02 — edited active.md
- 03:02 — edited MatchRecordView.vue
- 03:01 — edited LiveView.vue
- 03:01 — edited LiveView.vue
- 03:01 — edited MatchHistoryView.vue
- 02:59 — edited active.md
- 02:58 — edited active.md
- 19:58 — deployment confirmed live (check 7)
- Multiple deployment checks 2-6 returned 404 while Render was building
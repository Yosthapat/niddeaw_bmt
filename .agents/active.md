# Active Context

## Current Task
- Removed set-score entry entirely from match recording — admin now just picks win/loss/draw directly, no scores. Pushing now.

## Done Last Session
- Bigger avatars + name-below-avatar layout confirmed live on /matches and /live (verified via compiled JS chunk content, not CSS chunk — Tailwind utility classes live in the shared global stylesheet, not per-route CSS chunks, so checking those was a dead end)
- User asked to drop set-score entry entirely: admin should just record win/loss/draw directly, no scores needed
  - `MatchResultSubmit` model changed from `sets: list[SetScore]` to `winner: Winner` — admin declares the outcome directly instead of it being derived from scores
  - `submit_result` endpoint simplified: uses `payload.winner` directly, no longer writes `sets` on completion (stays whatever it was — null, since `confirm()` never sets it)
  - `Match.sets` was already nullable in both the Pydantic model and DB schema, so no migration needed; MatchHistoryView/MatchDetailView already render `sets: null` as "-" gracefully
  - `MatchRecordView.vue` rewritten: score input rows replaced with 3 buttons (team1 wins / draw / team2 wins), calling `recordMatchResult(matchId, winner)` directly
  - Removed now-dead `matchRecord.set`/`matchRecord.submit` i18n keys, added `matchRecord.wins`
  - mypy + pytest (25/25) and vue-tsc + vite build clean

## Next Steps
- Push and confirm both Render (backend) and Cloudflare (frontend) deploys are live
- Verify end-to-end against prod with the real admin token: confirm a throwaway match, submit via new winner-only endpoint, confirm it shows correctly on /matches (score box should show "-" since no sets)
- If full consistency desired later: extend the avatar/layout treatment to MatchmakingView.vue (admin) and MatchDetailView.vue too

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-22

## Checkpoint (auto)
- 03:17 — edited active.md
- 03:14 — edited matchmaking.py
- 03:14 — edited matchmaking.py
- 03:14 — edited matchmaking.py
- 03:14 — edited match.py
- 03:07 — edited active.md
# Active Context

## Current Task
- Added manual ELO override to the admin edit-member form — pushing now

## Done Last Session
- Confirmed live: /live polling fix (compiled catch block correctly guards on `J.value` falsy before setting error)
- User asked for a way to directly set a member's ELO score from the edit-member form, with the score applying immediately (not via match deltas)
- Backend: added `elo_score: int | None` to `PlayerUpdate` model; `update_player` endpoint now clamps to `SCORE_FLOOR` and recomputes `elo_level` via `get_tier()` whenever `elo_score` is present in the update payload — mirrors the same clamp/tier logic `create_player` already uses
- Frontend: `ManageMembersView.vue` edit form gained an ELO number input with a live `TierMascot` preview (via `useEloTier(editForm.elo_score).tier`) that updates as you type, wired into the existing `saveEdit`/`updatePlayer` call
- i18n: `members.eloScore` (th/en)
- mypy + pytest (25/25) and vue-tsc + vite build clean

## Next Steps
- Push and confirm both deploys live
- Verify against prod: PATCH a real member's elo_score via the new form field, confirm elo_level updates correctly and the change reflects immediately

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-22

## Checkpoint (auto)
- 00:15 — edited active.md
- 00:12 — edited players_admin.py
- 00:12 — edited player.py
- 07:35 — edited active.md
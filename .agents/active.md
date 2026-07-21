# Active Context

## Current Task
- Added a standalone "สร้างคู่เอง" (Create Custom Match) button to admin matchmaking — works even when fewer than 4 checked-in players means no auto-suggestion exists to edit. Pushing now.

## Done Last Session
- Explained existing "แก้คู่" (Edit Pair) capability to user, then user asked for a dedicated manual-create flow that doesn't depend on an auto-suggestion existing first
- Added `creatingCustom`/`customDraft` state + `startCustomMatch`/`cancelCustomMatch`/`confirmCustomMatch`/`customHasDuplicate`/`customIsComplete` to MatchmakingView.vue — a standalone form (2 dropdowns per team, reusing the existing `availablePool()` which already unions suggestions+waiting so it covers every checked-in-and-available player regardless of whether any suggestion groups formed) that calls the same `/api/admin/matchmaking/confirm` endpoint already in use — no backend changes needed
- i18n: `matchmaking.createCustom`, `matchmaking.pickPlayer` (th/en)
- `vue-tsc -b && vite build` clean; no backend risk since it's the same already-tested confirm endpoint

## Next Steps
- Push and confirm live
- Optional: add singles match support to the frontend UI (backend already supports type: 'single')

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-22

## Checkpoint (auto)
- 06:50 — edited active.md
- 06:49 — edited en.ts
- 06:49 — edited th.ts
- 06:49 — edited MatchmakingView.vue
- 06:49 — edited MatchmakingView.vue
- 06:49 — edited MatchmakingView.vue
- 06:47 — edited active.md
- 06:47 — edited active.md
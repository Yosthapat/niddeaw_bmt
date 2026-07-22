# Active Context

## Current Task
- Built session-scoped "lock pair" feature (user clarified: NOT a permanent profile setting, admin toggles it per-session since who someone comes with varies day to day) — pushing now

## Done Last Session
- Confirmed the cross-group-rotation matchmaking fix deployed healthy (health check 200 + authenticated sessions call worked)
- Built the full "lock pair" feature end to end:
  - `db/migrations/0012_locked_pairs.sql` (new table, session-scoped, cascade-deletes with the session) — **not yet run by user**
  - Backend: `LockedPair`/`LockedPairCreate` models; `POST /api/admin/matchmaking/locked-pairs` (409 if either player already locked with someone else this session) and `DELETE .../locked-pairs/{id}`; `MatchmakingQueueResponse` gained `locked_pairs: list[LockedPair]`
  - `matchmaking_service.suggest_doubles_pairings` gained an optional `locked_pairs` param: each active lock (both members currently checked in) is processed first, matched against either 2 solo players or one other complete locked pair — never split across teams — using the window search width already added for cross-group rotation; leftover players then run through the existing algorithm unchanged
  - `queue_service.py`: new `fetch_locked_pairs`, wired into `build_suggestions` and `build_queue`
  - 4 new tests (locked pair stays together even against better ELO-balance alternatives; two locked pairs face off correctly; a lock with a not-checked-in member is ignored; a lock waits together when there aren't enough others yet) — mypy clean, pytest 31/31
  - Frontend: `LockedPair` type, `createLockedPair`/`deleteLockedPair` API functions, new "คู่ล็อค" (Locked Pairs) section in MatchmakingView.vue between in-progress and suggestions — a "ล็อคคู่" button opens a 2-player picker (reusing `availablePool()`), locked pairs list shows with per-pair "ปลดล็อค" (unlock) buttons
  - `vue-tsc -b && vite build` clean

## Next Steps
- Push, give the user migration 0012 SQL to run in Supabase
- After migration runs: verify against prod — lock two real checked-in players, confirm suggestions keep them together across multiple refreshes, confirm unlock works, clean up test session/checkins afterward

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-23

## Checkpoint (auto)
- 01:54 — edited active.md
- 01:34 — edited matchmaking_service.py
- 01:33 — edited matchmaking.py
- 01:32 — edited matchmaking.py
- 01:32 — edited 0012_locked_pairs.sql
- 01:30 — edited active.md
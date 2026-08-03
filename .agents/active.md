# Active Context

## Current Task
- Wait for production deploy (b16aa31 + latest commit), then run end-to-end tests (admin login, member list, matchmaking) against live site

## Done Last Session
- Diagnosed root cause of production site failure: `frontend/.env.production` was missing, so Vite compiled with `undefined` as `VITE_API_BASE_URL`, breaking all API calls
- Created `frontend/.env.production` with correct backend URL, committed (not gitignored — it's a public URL, not a secret) (b16aa31)
- Changed `/members` page sort order from points-descending to alphabetical
  (A-Z): backend `list_players` in `players.py` now sorts by
  `nickname.lower()` instead of points. Ranking page is unaffected — it
  uses a separate `/api/ranking` endpoint entirely.
- Backend mypy + all 31 tests pass, frontend type-check + build clean,
  re-verified the correct API URL is still baked into this build

## Next Steps
- User deploys via `wrangler deploy`
- Run end-to-end tests on live site: admin login flow, member list
  alphabetical order, matchmaking functionality
- Establish e2e test suite to prevent this class of build-time env bug recurring

## Blockers
- Waiting for production deploy to be executed

## Last Updated
- Claude Code — 2026-08-04

## Checkpoint (auto)
- 03:08 — edited active.md
- 03:07 — edited MemberListView.vue
- 03:07 — edited players.py
- 02:59 — edited active.md
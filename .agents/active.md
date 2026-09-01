# Active Context

## Current Task
- PR open to pin Node version for Cloudflare Workers Builds; once merged
  and deployed, run end-to-end tests (admin login, member list,
  matchmaking) against live site

## Done This Session
- Found that b16aa31 (the VITE_API_BASE_URL fix) never actually reached
  production: Cloudflare's "Build history" shows every build since
  `2c4d8a1` failing, so the site stayed on that old broken deploy for
  nearly a month even though `main` had the fix
- Root-caused the build failures: `vite@8` requires Node
  `^20.19.0 || >=22.12.0`; nothing in the repo pinned a Node version, so
  Cloudflare's build image (older than that) fails the build outright
  before it ever gets to the actual code
- Added `.nvmrc` (repo root + `frontend/`, `22.12.0`) and
  `engines.node` in `frontend/package.json` to pin it explicitly;
  documented in `deploy/cloudflare/README.md`
- Verified `cd frontend && npm install && npm run build` (the exact
  Cloudflare build command) succeeds clean with these changes

## Done Previous Session (2026-08-04)
- Diagnosed root cause of production site failure: `frontend/.env.production` was missing, so Vite compiled with `undefined` as `VITE_API_BASE_URL`, breaking all API calls
- Created `frontend/.env.production` with correct backend URL, committed (not gitignored — it's a public URL, not a secret) (b16aa31)
- Changed `/members` page sort order from points-descending to alphabetical
  (A-Z): backend `list_players` in `players.py` now sorts by
  `nickname.lower()` instead of points. Ranking page is unaffected — it
  uses a separate `/api/ranking` endpoint entirely.
- Backend mypy + all 31 tests pass, frontend type-check + build clean,
  re-verified the correct API URL is still baked into this build

## Next Steps
- Merge the Node-version-pin PR, confirm Cloudflare's next build goes
  green, confirm the live site actually serves the new deploy
- Run end-to-end tests on live site: admin login flow, member list
  alphabetical order, matchmaking functionality
- Set up an uptime monitor (e.g. UptimeRobot) hitting the frontend and
  backend `/health` so a dead build/site is caught immediately instead
  of silently for weeks, like this one was
- Establish e2e test suite to prevent this class of build-time env bug recurring

## Blockers
- None — fix is ready, needs PR review/merge + a real Cloudflare deploy to confirm

## Last Updated
- Claude Code — 2026-09-01

## Checkpoint (auto)
- 03:08 — edited active.md
- 03:07 — edited MemberListView.vue
- 03:07 — edited players.py
- 02:59 — edited active.md
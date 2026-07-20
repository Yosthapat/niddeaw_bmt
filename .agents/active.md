# Active Context

## Current Task
- Built a public "Live" queue page so players can see if their match is in progress / how many groups are ahead, and pushing this deploy

## Done Last Session
- Fixed and confirmed live: home page crash from unescaped `@` in vue-i18n contactBody string (commit 278d469)
- Added public live-queue feature:
  - Extracted `app/services/queue_service.py` (I/O layer) out of the admin matchmaking router so both admin and public routers share the same queue-building logic without duplication
  - Added `LiveQueueResponse` model + new public `GET /api/live` endpoint (`app/routers/public/live.py`) — self-resolves the currently open session server-side, no auth/session_id needed from the caller
  - Admin matchmaking router (`/api/admin/matchmaking/*`) refactored to call `queue_service` instead of duplicated private functions — behavior unchanged
  - New frontend `LiveView.vue` at `/live` route: shows in-progress matches (avatar clusters), next suggested pairing, and the waiting queue with estimated wait — polls every 7s like the admin matchmaking screen
  - Added nav link + `nav.live` / `live.*` i18n keys (th/en)
  - Completed matches still surface automatically on `/matches` once admin submits a result — no extra work needed there, already worked via existing completed-match filtering
- Backend: mypy (39 files) and pytest (25/25) clean; Frontend: `vue-tsc -b && vite build` clean

## Next Steps
- Commit, push, confirm both Render (backend) and Cloudflare (frontend) deploys are live
- Manually verify `/live` on production once there's an open session with checked-in players
- Re-run full authenticated admin flow (login → checkin → matchmaking → billing → revenue) as a fresh end-to-end QA pass if desired — still not re-run since the i18n/stamps changes

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-21

## Checkpoint (auto)
- 06:08 — edited active.md
- 05:24 — edited active.md
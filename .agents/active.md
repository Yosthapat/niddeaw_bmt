# Active Context

## Current Task
Deploying Phase 1 scaffold to real infrastructure (guided walkthrough with user). Backend (Render) is live and verified. Frontend (Cloudflare Workers static assets) deploy is stuck on a dashboard quirk — troubleshooting in progress.

## Done Last Session
- **Supabase**: project created (`qzwrrrgxjstdcnqelidr`), all 5 migrations run, `service_role` key captured.
- **Render backend**: deployed at `https://niddeaw-bmt.onrender.com`. Hit a real bug — PDM's private-Python management doesn't persist between Render's build/runtime steps, causing `pdm run uvicorn` to fail with "not found in PATH". Fixed by switching `deploy/render.yaml` to `pdm export -o requirements.txt && pip install -r requirements.txt` for build, plain `uvicorn ...` for start, plus pinning `PYTHON_VERSION`. Verified locally (fresh venv + pip install + `which uvicorn`) before pushing. **`/health` and `/api/players` both confirmed working against real Supabase.**
- **Cloudflare**: Cloudflare's dashboard has moved to a unified "Workers Builds" flow (no more classic Pages root-directory/output-directory fields) — added a repo-root `wrangler.jsonc` (assets.directory → `./frontend/dist`) to match. Project created (`niddeaw-bmt`), connected to GitHub, `VITE_API_BASE_URL` env var set.
- **Current blocker**: first deploy served Cloudflare's default "Hello world" placeholder because the Build Command field didn't get saved from the onboarding wizard. Fixed via Settings → Build (build command now correctly shows `cd frontend && npm install && npm run build` there). But clicking **Retry build** on the old failed build entry replays *that build's original stale config snapshot* (still shows "Build command: None"), not the current Settings.

## Next Steps
- Trigger a genuinely fresh deployment (not a "Retry" of the old stale build) so it picks up the current, correct Settings — pushing a new commit is the reliable way since Retry appears to replay historical config.
- Once deployed, verify `https://niddeaw-bmt.yosthapatk-mbai.workers.dev/` serves the real Vue app (not "Hello world"), then update Render's `CORS_ORIGINS` to match.
- Remaining tutorial steps not yet done: cron-job.org keepalive ping, create real admin user (bcrypt hash + insert), log into `/admin/settings` to set real PromptPay ID + rate.

## Blockers
- Cloudflare "Retry build" not respecting updated Settings — working around by pushing a fresh commit instead.

## Last Updated
- Claude Code — 2026-07-20

## Checkpoint (auto)
- 03:19 — edited active.md

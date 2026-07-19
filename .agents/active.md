# Active Context

## Current Task
- None — Phase 1 complete. Waiting on user to provision cloud credentials and deploy.

## Done Last Session
- Reviewed ISSUE_beerminton_webapp.md and resolved 6 design risks before coding: player-auth decision (no player login in Phase 1), frontend-never-touches-Supabase-directly security, match score format (sets), realtime vs polling (polling), asset paths, and all documented in issue file's "Decisions Resolved" section.
- **Backend** (FastAPI + PDM, 19 tests passing, mypy strict clean): full pydantic models, JWT admin auth with direct bcrypt lib (passlib's bcrypt backend is broken with bcrypt≥4.1), public read-only routers (players/ranking/hall-of-fame/matches), admin routers (sessions/checkins/players/settings/matchmaking/billing), ELO service (K=32, 5 tiers), matchmaking with ELO-balance + fairness penalty, billing (30-min rounding + 5-min grace), and self-implemented PromptPay QR (EMVCo TLV + CRC16, verified byte-for-byte against reference test vectors).
- **Database** (5 SQL migrations): schema, indexes, club_settings seed, RLS deny-by-default security, avatars storage bucket, and dev seed data (db/seed/seed_dev.sql).
- **Frontend** (Vue3 + TS + Vite + Tailwind v4 + PWA, vue-tsc and vite build clean): full router (5 public + 7 admin routes), Pinia auth/players/sessions stores, all 12 views wired to real backend, black/pink theme with ELO tier colors, PWA manifest/icons generated from club logo.
- **Deploy configs** scaffolded (Render, Cloudflare Pages, ENV_SETUP.md checklist) but not yet run — no cloud accounts provisioned yet.
- Verified end-to-end locally: backend boots, /health OK, all 24 routes in OpenAPI, frontend compiles and serves all views.

## Next Steps
- User provisions Supabase/Render/Cloudflare Pages accounts, then follow `deploy/ENV_SETUP.md` to go live.
- Review `git status`/`git diff` and commit when ready.
- Consider running `/code-review` before first commit.

## Blockers
- None — waiting on user-provided cloud credentials (by design).

## Last Updated
- Claude Code — 2026-07-20

## Checkpoint (auto)
- 01:17 — edited active.md

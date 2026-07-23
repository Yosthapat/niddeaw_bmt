# Active Context

## Current Task
- Awaiting deployment to production via `npx wrangler deploy` (need Cloudflare auth)

## Done Last Session
- **Session location dropdown**: Implemented dropdown in "สร้าง session" form with three options (KB badminton court โยธินพัฒนา, Guy badminton court, Custom free-text); updated SessionPicker.vue, MatchmakingView.vue, and i18n translations (en.ts, th.ts)
- **Lock-pair error handling fix**: Fixed race condition where `refreshQueue()` failure after successful lock creation was misreported as lock failure; improved both `createLockedPair` and `unlockPair` error handling
- **Frontend build**: Ran full TypeScript build, verified clean output, PWA assets generated (41 precache entries)

## Next Steps
- User runs `wrangler login` (interactively, opens OAuth) in their terminal
- User runs `npx wrangler deploy` from repo root to deploy both fixes
- Confirm deployment success in production

## Blockers
- Wrangler auth token requires interactive OAuth login (non-interactive environment cannot proceed)
- CLOUDFLARE_API_TOKEN env var not set in this session

## Last Updated
- Claude Code — July 23, 2026

## Checkpoint (auto)
- 07:04 — edited active.md
- 07:04 — frontend build complete (TSC_OK, 214ms)
- 07:01 — edited SessionPicker.vue, en.ts, th.ts
- 00:03 — attempted wrangler deploy (needs auth)
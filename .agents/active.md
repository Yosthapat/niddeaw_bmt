# Active Context

## Current Task
- Fixed missing member photos on admin Matchmaking + Billing pages (showing initials-only fallback instead of real avatars) — pushing now

## Done Last Session
- Confirmed DRAW label fix live (matches.draw in both stamp usages)
- User screenshotted admin /admin/matchmaking and /admin/billing showing initials-only avatar circles instead of real member photos, asked for them to match other pages
- Root cause: both `PlayerAvatar` usages in each file were missing the `:avatar-url` prop entirely (only `:name` was passed, so the component always fell back to initials) — a real bug, not a data issue
- Audited every other admin view's PlayerAvatar usage (CheckinView, ManageMembersView) — both already correctly pass avatar-url; the bug was isolated to exactly these two files
- Added `avatarOf(playerId)` helper to both MatchmakingView.vue and BillingView.vue, wired into every PlayerAvatar call: MatchmakingView's in-progress list (2), waiting queue (1), and the suggestions list (2, which also had zero avatars at all before — added avatar clusters there matching the in-progress section's style); BillingView's unbilled list (1) and billings list (1)
- `vue-tsc -b && vite build` clean

## Next Steps
- Push and confirm live
- Optional: add UI support for singles matches (backend already supports type: 'single')

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-22

## Checkpoint (auto)
- 07:04 — edited active.md
- 07:03 — edited BillingView.vue
- 07:03 — edited BillingView.vue
- 07:03 — edited BillingView.vue
- 07:03 — edited MatchmakingView.vue
- 07:02 — edited MatchmakingView.vue
- 07:02 — edited MatchmakingView.vue
- 07:02 — edited MatchmakingView.vue
- 07:02 — edited MatchmakingView.vue
- 07:01 — edited active.md
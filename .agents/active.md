# Active Context

## Current Task
- Deploy the Absinthe rainbow-color change to production (needs `npx wrangler deploy` from user's terminal)

## Done Last Session
- Absinthe tier (ELO >= 2100) fully deployed to production and verified live
- Added rainbow gradient treatment for Absinthe specifically (top/rarest rank):
  - New `--gradient-tier-absinthe` CSS var in tailwind.css (7-stop rainbow linear-gradient)
  - `useEloTier.ts` gained `gradient?` field on TierInfo plus two shared helpers,
    `tierTextStyle()` (gradient background-clip text, falls back to solid color)
    and `tierSwatchStyle()` (gradient background, falls back to solid backgroundColor)
  - Applied via the helpers in `EloBadge.vue` (used everywhere — member list,
    ranking, hall of fame, checkin, profile, match detail), `HomeView.vue`
    tier showcase strip, and `ManageMembersView.vue` starting-tier picker
  - Every other tier unaffected — helpers fall back to the existing solid colorVar
  - Frontend type-check and build both clean

## Next Steps
- User runs `npx wrangler deploy` from their terminal to push the rainbow-color change live

## Blockers
- Wrangler auth not available in non-interactive environment; user must deploy from their own terminal with API token

## Last Updated
- Claude Code — 2026-08-04

## Checkpoint (auto)
- 01:54 — edited active.md

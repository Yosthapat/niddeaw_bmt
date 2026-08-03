# Active Context

## Current Task
- None — all pending work committed. Awaiting next request.

## Done Last Session
- Added "Absinthe" as a new highest ELO tier above Vodka:
  - Backend: `EloTier` literal, `_TIER_THRESHOLDS` (Vodka 1900-2099, Absinthe >=2100), tests updated
  - Migration `0013_absinthe_tier.sql` (constraint + recompute elo_level, following the wine-tier precedent)
  - Frontend: `EloTier` type, `useEloTier` composable, `TierMascot` labels, tier lists in `HomeView.vue` and `ManageMembersView.vue`, new `--color-tier-absinthe` CSS var
  - Mascot artwork saved to `frontend/public/tiers/absinthe.webp`, background removed via corner-seeded flood-fill (same method as the other 7 mascots), resized to 320x320 to match
  - Backend: mypy clean, all 31 tests pass. Frontend: vue-tsc clean, build clean
- Replaced home ad banner with new "Friday Night" promo artwork, adjusted `AdCarousel`'s aspect ratio to match (pushed as 94be2fc)

## Next Steps
- Commit + push the Absinthe tier work
- User still needs to run the `0013_absinthe_tier.sql` migration in Supabase
- User still needs `CLOUDFLARE_API_TOKEN` (or `wrangler login`) in their own terminal to deploy — same standing blocker as previous sessions

## Blockers
- Wrangler auth not available in this non-interactive environment — deploy must be run by the user

## Last Updated
- Claude Code — 2026-08-04

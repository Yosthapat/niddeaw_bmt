# Active Context

## Current Task
- Added a new "Wine" ELO tier and reordered all tiers by rising alcohol content — pushing this now; member_seq renumber SQL is still separately pending user execution

## Done Last Session
- Diagnosed member sequence numbering issue and gave the user a ready-to-run 3-phase SQL script (bump to 100k+, renumber 1-N by created_at, reset sequence) — not yet confirmed run
- Added "Wine" tier per user request, reordered all 7 tiers by rising ABV: Milk(0%) < Beer(~5%) < Highball(~7-9%) < Wine(~12-13%) < Soju(~16-20%) < Whisky(~40%) < Vodka(~40%+)
  - Backend: `elo_service.py` `_TIER_THRESHOLDS` reordered/expanded (900/1100/1300/1500/1700/1900), `EloTier` Literal in `models/player.py`, `test_elo_service.py` boundaries updated — mypy + pytest (25/25) clean
  - DB: `db/migrations/0010_wine_tier.sql` — updates the `players_elo_level_check` constraint AND recomputes `elo_level` for all existing players via CASE (unlike the 0007 migration, prod now has real players, so stale stored tier labels needed a one-time fix, not just new matches triggering it) — **not yet run by user**
  - Frontend: `types/player.ts` EloTier union, `useEloTier.ts` TIERS array, `tailwind.css` `--color-tier-wine: #7c2d42` (deep burgundy, distinct from whisky's rust `#a8503f`), new hand-drawn wine-glass mascot in `TierMascot.vue` (calm/mellow expression, sits between highball and soju), `ManageMembersView.vue` tierOptions, `HomeView.vue` tiers legend — all reordered consistently
  - `vue-tsc -b && vite build` clean

## Next Steps
- User still needs to run BOTH pending SQL scripts in Supabase SQL Editor: (1) the member_seq renumber, (2) `db/migrations/0010_wine_tier.sql`
- Push wine-tier code, confirm deploy live
- After migration 0010 runs, verify via API that existing players show correct new tier labels for their unchanged elo_score

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-22

## Checkpoint (auto)
- 02:17 — edited active.md
- 02:16 — edited TierMascot.vue
- 02:15 — edited HomeView.vue
- 02:15 — edited ManageMembersView.vue
- 02:15 — edited useEloTier.ts
- 02:15 — edited tailwind.css
- 02:15 — edited player.ts
- 02:14 — edited 0010_wine_tier.sql
- 02:14 — edited test_elo_service.py
- 02:14 — edited elo_service.py
- 02:14 — edited player.py
- 02:10 — edited active.md
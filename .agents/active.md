# Active Context

## Current Task
- Removed the Hall of Fame quick-link card from the home page grid (was still showing there even after unlinking it from the header nav) — pushing this fix

## Done Last Session
- Confirmed live via MD5 hash match: apple-touch-icon-180x180.png fix (regenerated full-bleed, no more baked-in white margin) — iOS caches the icon on-device, so a plain refresh won't show it; user needs to remove and re-add "Add to Home Screen" to see the fix
- Removed the "03 Hall of Fame" card from HomeView.vue's `quickLinks` grid — user flagged it was still showing there even though it's already unlinked from the header nav (not in use yet)
- Renumbered remaining quick links (01 สมาชิก, 02 อันดับ, 03 ผลแมตช์) and changed the grid from `grid-cols-2 sm:grid-cols-4` to `grid-cols-1 sm:grid-cols-3` so 3 cards lay out cleanly instead of leaving an awkward gap
- `vue-tsc -b && vite build` clean

## Next Steps
- Push and confirm live
- Whenever Hall of Fame is ready to use again: re-add its entry to `publicLinks` in AppHeader.vue AND `quickLinks` in HomeView.vue (both were hidden, not deleted)

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-21

## Checkpoint (auto)
- 18:40 — edited active.md
- 18:40 — edited HomeView.vue
- 18:39 — edited HomeView.vue
- 18:39 — edited active.md
- 18:34 — edited active.md
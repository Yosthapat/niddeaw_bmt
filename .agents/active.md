# Active Context

## Current Task
- Ad carousel image received, converted to WebP, wired in — pushing this deploy

## Done Last Session
- Built `AdCarousel.vue`: auto-crossfade every 5s, dot indicators when >1 image, supports up to 4 images, sits at the top of HomeView above the logo/hero
- User placed `cover-page.png` (1942x809, 2.1MB) — converted to `cover-page.webp` at quality 82 (217KB, ~90% smaller, no visible quality loss) since a 2MB PNG hero banner would meaningfully slow the homepage on mobile data at the court
- `frontend/public/ads/` is the drop folder for future slides — just add the file and list its path in the `ads` array in `HomeView.vue` (max 4)
- `vue-tsc -b && vite build` clean

## Next Steps
- Push and confirm the deploy is live, spot-check the banner renders and crossfades correctly
- When more ad images arrive, convert to WebP the same way before adding to the `ads` array

## Last Updated
- Claude Code — 2026-07-21

## Checkpoint (auto)
- 18:00 — edited active.md
- 17:58 — edited active.md
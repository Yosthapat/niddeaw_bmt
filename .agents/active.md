# Active Context

## Current Task
- Urgent fix: ad banner was cropping the image (object-cover + mismatched aspect ratio) and the old redundant logo badge was still showing below it — pushing fix now

## Done Last Session
- AdCarousel.vue: switched `object-cover` → `object-contain` and changed the fixed aspect ratio to `aspect-[12/5]` (matches cover-page.webp's actual 1942x809 ratio) so the full image always shows, never cropped — container bg is already brand-black so any letterbox bars for future differently-shaped images are invisible
- HomeView.vue: removed the small square logo badge (pwa-icon) that sat below the new ad banner — user flagged it as redundant/already-requested-removed, the ad banner itself already carries the club branding
- `vue-tsc -b && vite build` clean

## Next Steps
- Push and confirm live, spot-check the banner shows the full Friday Night flyer with no cropping and the redundant logo badge is gone
- When more ad images arrive: convert to WebP and add to `ads` array in HomeView.vue (max 4)

## Blockers
- None

## Last Updated
- Claude Code — 2026-07-21

## Checkpoint (auto)
- 18:32 — edited active.md
- 18:31 — edited HomeView.vue
- 18:31 — edited AdCarousel.vue
- 18:04 — edited active.md
# Active Context

## Current Task
- Regenerated apple-touch-icon-180x180.png (had a real bug: 15%-per-side opaque white margin baked in, unlike the sibling icons) — pushing this fix

## Done Last Session
- Confirmed live: ad banner cropping fix (object-contain + matched aspect ratio) and redundant logo badge removal
- Found and fixed `frontend/public/pwa-icons/apple-touch-icon-180x180.png`: had a 27px opaque white margin per side (content bbox only 27,27–152,152 of a 180x180 canvas) — this is what iOS uses for "Add to Home Screen", so it rendered with a visible white border unlike every other app icon
  - Regenerated from `pwa-512x512.png` (the full-bleed transparent master icon): cropped to its content bbox, flattened onto solid brand-black (matches the icon's own black backing so edges stay seamless), resized to 180x180
  - Checked siblings for the same bug: `pwa-192x192.png`/`pwa-64x64.png` already near-full-bleed (~2.5% margin, fine); `maskable-icon-512x512.png` has an intentional ~15% safe-zone margin per the Android maskable-icon spec — left untouched, that one's correct as-is
- `vue-tsc -b && vite build` clean

## Next Steps
- Push, confirm deploy live, and ask user to re-add the home screen icon (iOS caches the old icon PNG on-device — a plain page refresh won't update it, they'll need to remove and re-add "Add to Home Screen")

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-21

## Checkpoint (auto)
- 18:39 — edited active.md
- 18:34 — edited active.md
# Active Context

## Current Task
- Home page contact section: reworded awkward "โดย Beerminton" copy, replaced inline LINE handle text with clickable LINE OA + TikTok badges — pushing this deploy

## Done Last Session
- Completed live-queue feature deployment and verification (backend `/api/live` on Render, frontend `/live` on Cloudflare, both confirmed live)
- Reworded `home.contactTitle` from "ติดต่อผู้จัดก๊วน โดย Beerminton" (ambiguous referent) to "ติดต่อผู้จัดก๊วน — Beerminton" (th) / "Contact the Club Organizer — Beerminton" (en)
- Trimmed `home.contactBody` to drop the inline "LINE OA : @369iojcn" mention, since that's now a clickable badge instead of plain text
- Added two own-drawn (not brand-logo) icon badges to the HomeView contact section: LINE OA → `https://line.me/R/ti/p/@369iojcn`, TikTok → `https://www.tiktok.com/@nidde4w`, both `target="_blank" rel="noopener noreferrer"`
- `vue-tsc -b && vite build` clean

## Next Steps
- Push and confirm the Cloudflare deploy is live, spot-check the two contact badges actually open LINE/TikTok correctly
- Test `/live` during an actual gameplay session with checked-in players
- Optional: enhance `/live` UI further (highlight estimated wait more prominently, player search)

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-21

## Checkpoint (auto)
- 17:02 — edited active.md
- 17:01 — edited HomeView.vue
- 17:01 — edited HomeView.vue
- 17:01 — edited en.ts
- 17:01 — edited th.ts
- 06:14 — edited active.md
# Active Context

## Current Task
- Removed the entire quick-links card grid from the home page per user request (redundant with the header nav) — pushing this fix

## Done Last Session
- Confirmed via content-check (not exact hash match — Cloudflare's build can produce a different bundler hash than a local build for identical source, so hash comparison isn't reliable across environments) that the Hall-of-Fame-card-removed deploy was live
- Removed the whole `<nav>` quick-links section (สมาชิก/อันดับ/ผลแมตช์ cards) from HomeView.vue — user said it's redundant now that the same links are already in the header nav bar, and it was cluttering the home page
- Deleted the now-unused `quickLinks` computed from the script, and the now-dead `nav.reveal` CSS rules (nth-child stagger delays, reduced-motion override) from the scoped style block
- `vue-tsc -b && vite build` clean

## Next Steps
- Push and confirm live
- When Hall of Fame is ready again: only AppHeader.vue's `publicLinks` needs the entry back now (the HomeView quick-links grid it used to also live in is gone entirely)

## Last Updated
- Claude Code — 2026-07-21

## Checkpoint (auto)
- 18:47 — edited active.md
- 18:46 — edited HomeView.vue
- 18:46 — edited HomeView.vue
- 18:46 — edited HomeView.vue
- 18:45 — edited HomeView.vue
- 18:44 — edited active.md
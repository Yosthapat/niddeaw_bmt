# Active Context

## Current Task
- Removed stray scrollbar from header nav, hid the Hall of Fame nav link temporarily — pushing this deploy

## Done Last Session
- Updated home page contact section: reworded title, replaced inline LINE handle text with clickable LINE OA + TikTok icon badges — confirmed live on production
- AppHeader.vue: removed `overflow-x-auto` from the nav (was rendering a stray pink scrollbar-thumb pill via the site's themed `*::-webkit-scrollbar` styling even though the nav never actually needed to scroll)
- AppHeader.vue: temporarily removed the Hall of Fame entry from `publicLinks` per user request ("ยังไม่ไช้") — the `/hall-of-fame` route + view are untouched, just unlinked from the header nav; easy to re-add the one array entry later
- `vue-tsc -b && vite build` clean

## Next Steps
- Confirm this deploy is live on Cloudflare
- Test `/live` during actual gameplay with checked-in players
- Re-add the Hall of Fame nav link whenever the user says it's ready to use

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-21

## Checkpoint (auto)
- 17:09 — edited active.md
- 17:08 — edited AppHeader.vue
- 17:08 — edited AppHeader.vue
- 17:04 — edited active.md
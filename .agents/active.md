# Active Context

## Current Task
- Rebuilt admin matchmaking's in-progress + suggestions layouts to match /live's vertical avatar-on-top/name-below style — pushing now

## Done Last Session
- Confirmed live: avatar overlap fix (-space-x -> gap) across /live, /matches, admin matchmaking
- User screenshotted the admin matchmaking "แนะนำคู่ถัดไป" suggestions row looking cramped (name text wrapping, colliding with avatars) on mobile width, asked to match /live's layout
- Rebuilt MatchmakingView.vue's in-progress list AND suggestions list: both now use the vertical stack (avatar cluster centered on top, name centered below) instead of the old horizontal name-beside-avatar row
- Suggestions list's แก้คู่/ยืนยัน buttons moved to their own centered row below the team blocks, matching how the in-progress list already puts Record Result/Cancel below — edit-mode form (dropdowns) untouched
- `vue-tsc -b && vite build` clean

## Next Steps
- Push and confirm live
- Optional: add UI support for singles matches (backend already supports type: 'single')

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-22

## Checkpoint (auto)
- 07:10 — edited active.md
- 07:09 — edited MatchmakingView.vue
- 07:09 — edited MatchmakingView.vue
- 07:08 — edited active.md